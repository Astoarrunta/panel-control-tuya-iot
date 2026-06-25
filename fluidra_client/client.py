"""
Cliente de alto nivel para la API privada de Fluidra Connect.

Uso típico:

    client = FluidraClient(username="tu_email", password="tu_password")
    client.login()

    dispositivos = client.list_devices()
    device_id = dispositivos[0]["id"]

    componentes = client.get_device_components(device_id)
    client.set_component_value(device_id, component_id=14, value=0)  # Smart
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from .auth import FluidraAuth, FluidraAuthError
from .const import (
    API_CONSUMER_URL,
    API_DEVICE_COMPONENTS_URL,
    API_DEVICE_UICONFIG_URL,
    API_DEVICES_URL,
    API_SET_COMPONENT_VALUE_URL,
    API_USER_POOLS_URL,
    API_USER_PROFILE_URL,
    DEFAULT_API_RATE_LIMIT,
    ERROR_CODES,
    HEATPUMP_MODES,
    HEATPUMP_MODES_REVERSE,
)

logger = logging.getLogger("fluidra_client")


class FluidraAPIError(Exception):
    """Error al llamar a la API de Fluidra (HTTP no-200, timeout, etc.)."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class FluidraClient:
    """Cliente síncrono (requests) para la API de Fluidra Connect."""

    def __init__(
        self,
        username: str,
        password: str,
        rate_limit_per_minute: int = DEFAULT_API_RATE_LIMIT,
        timeout: float = 15.0,
    ):
        self.auth = FluidraAuth(username, password)
        self.timeout = timeout
        self.rate_limit_per_minute = rate_limit_per_minute
        self._call_timestamps: List[float] = []
        self._session = requests.Session()

    # ── Sesión ───────────────────────────────────────────────────────────

    def login(self) -> None:
        """Autentica explícitamente. Lanza FluidraAuthError si falla."""
        self.auth.authenticate()
        logger.info("Login en Fluidra Connect correcto para %s", self.auth.username)

    # ── Llamada HTTP genérica con rate limiting y manejo de errores ─────

    def _request(self, method: str, url: str, **kwargs) -> Any:
        self._respect_rate_limit()
        headers = self.auth.get_auth_headers()
        headers.update(kwargs.pop("headers", {}) or {})

        try:
            response = self._session.request(
                method, url, headers=headers, timeout=self.timeout, **kwargs
            )
        except requests.RequestException as exc:
            raise FluidraAPIError(f"Error de red llamando a {url}: {exc}") from exc

        self._call_timestamps.append(time.time())

        if response.status_code == 200:
            if not response.content:
                return None
            try:
                return response.json()
            except ValueError:
                return response.text
        if response.status_code == 401:
            raise FluidraAPIError(
                f"401 No autorizado en {url}. Token inválido o caducado.",
                status_code=401,
            )
        if response.status_code == 403:
            raise FluidraAPIError(
                f"403 Prohibido en {url}. Puede que este endpoint no esté "
                f"disponible para tu cuenta/dispositivo.",
                status_code=403,
            )
        raise FluidraAPIError(
            f"{response.status_code} llamando a {url}: {response.text[:300]}",
            status_code=response.status_code,
        )

    def _respect_rate_limit(self) -> None:
        now = time.time()
        self._call_timestamps = [t for t in self._call_timestamps if now - t < 60]
        if len(self._call_timestamps) >= self.rate_limit_per_minute:
            sleep_for = 60 - (now - self._call_timestamps[0])
            if sleep_for > 0:
                logger.warning("Rate limit alcanzado, esperando %.1fs", sleep_for)
                time.sleep(sleep_for)

    # ── Descubrimiento ───────────────────────────────────────────────────

    def list_devices(self) -> List[Dict[str, Any]]:
        """
        Lista todos los dispositivos (bombas de calor, depuradoras,
        cloradores, etc.) vinculados a tu cuenta de Fluidra Pool.
        """
        raw = self._request("GET", API_DEVICES_URL)
        devices = self._normalize_list(raw)
        return [self._process_device(d) for d in devices]

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        for device in self.list_devices():
            if device["id"] == device_id:
                return device
        return None

    def get_user_profile(self) -> Dict[str, Any]:
        return self._request("GET", API_USER_PROFILE_URL) or {}

    def get_consumer_info(self) -> Dict[str, Any]:
        return self._request("GET", API_CONSUMER_URL) or {}

    def get_user_pools(self) -> List[Dict[str, Any]]:
        raw = self._request("GET", API_USER_POOLS_URL)
        return self._normalize_list(raw)

    # ── Lectura de estado ────────────────────────────────────────────────

    def get_device_components(self, device_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Devuelve los componentes (sensores y controles) de un dispositivo,
        indexados por component_id. Cada bomba de calor expone temperatura
        actual, temperatura objetivo, modo, estado de errores, etc. como
        "componentes" numerados — el mapeo exacto de IDs varía por modelo
        y firmware, por eso conviene inspeccionarlos al menos una vez.
        """
        url = API_DEVICE_COMPONENTS_URL.format(device_id=device_id)
        raw = self._request("GET", url)
        components = self._normalize_list(raw)
        return {
            str(c["id"]): c
            for c in components
            if c.get("id") is not None
        }

    def get_device_uiconfig(self, device_id: str) -> Dict[str, Any]:
        """Configuración de UI del dispositivo (etiquetas, rangos, etc.)."""
        url = API_DEVICE_UICONFIG_URL.format(device_id=device_id)
        return self._request("GET", url) or {}

    # ── Control ──────────────────────────────────────────────────────────

    def set_component_value(self, device_id: str, component_id: Any, value: Any) -> None:
        """
        Cambia el valor deseado ("desiredValue") de un componente concreto.
        Esto es lo que usan internamente set_heatpump_mode y
        set_target_temperature.
        """
        url = API_SET_COMPONENT_VALUE_URL.format(
            device_id=device_id, component_id=component_id
        )
        payload = {"desiredValue": value}
        self._request(
            "PUT",
            url,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        logger.info(
            "Componente %s del dispositivo %s actualizado a %r",
            component_id, device_id, value,
        )

    def set_heatpump_mode(self, device_id: str, mode: str, mode_component_id: int = 14) -> None:
        """
        Cambia el modo de la bomba de calor.

        mode: uno de "smart_heating_cooling", "boost_heating",
              "silence_heating", "boost_cooling", "smart_cooling",
              "silence_cooling", "off".
        mode_component_id: id del componente de modo. En la mayoría de
              equipos Fluidra/Zodiac/AstralPool observados es el 14, pero
              verifícalo con get_device_components() en tu Eco Elyo
              concreto antes de confiar en este valor por defecto.
        """
        if mode not in HEATPUMP_MODES_REVERSE:
            valid = ", ".join(HEATPUMP_MODES_REVERSE)
            raise ValueError(f"Modo '{mode}' no reconocido. Válidos: {valid}")
        numeric_value = HEATPUMP_MODES_REVERSE[mode]
        self.set_component_value(device_id, mode_component_id, numeric_value)

    def set_target_temperature(
        self, device_id: str, temperature_c: float, temp_component_id: int = 1
    ) -> None:
        """
        Cambia la temperatura objetivo (°C). Rango habitual: 10-40°C con
        pasos de 0.5°C. temp_component_id por defecto es una suposición
        razonable (1) — confírmalo inspeccionando los componentes de tu
        equipo: busca el que tenga unit="C" o similar y sea escribible.
        """
        self.set_component_value(device_id, temp_component_id, temperature_c)

    # ── Helpers de error ─────────────────────────────────────────────────

    @staticmethod
    def describe_error_code(code: str) -> str:
        return ERROR_CODES.get(code, "Código de error desconocido")

    # ── Normalización interna ────────────────────────────────────────────

    @staticmethod
    def _normalize_list(raw: Any) -> List[Dict[str, Any]]:
        """La API de Fluidra a veces devuelve una lista, a veces un dict
        con clave 'data', y a veces un único objeto. Normalizamos a lista."""
        if raw is None:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            if isinstance(raw.get("data"), list):
                return raw["data"]
            if "id" in raw:
                return [raw]
        return []

    def _process_device(self, device: Dict[str, Any]) -> Dict[str, Any]:
        connectivity = device.get("connectivity", {}) or {}
        info = device.get("info", {}) or {}
        alarms = device.get("alarms", []) or []

        error_alarms = [a for a in alarms if a.get("type") == "error"]
        warning_alarms = [a for a in alarms if a.get("type") == "warning"]

        alarm_status = "normal"
        error_code = None
        error_message = None
        if error_alarms:
            alarm_status = "error"
            error_alarm = error_alarms[0]
            error_code = error_alarm.get("errorCode") or error_alarm.get("code")
            error_message = (
                error_alarm.get("message")
                or error_alarm.get("text")
                or self.describe_error_code(error_code or "")
            )
        elif warning_alarms:
            alarm_status = "warning"

        return {
            "id": device.get("id"),
            "name": device.get("name") or info.get("name") or "Dispositivo sin nombre",
            "model": info.get("family"),
            "serial_number": device.get("sn") or device.get("serialNumber"),
            "type": device.get("type"),
            "status": device.get("status"),
            "firmware": device.get("vr"),
            "connected": bool(connectivity.get("connected")),
            "pool_id": device.get("poolId"),
            "alarm_status": alarm_status,
            "alarm_count": len(alarms),
            "error_code": error_code,
            "error_message": error_message,
            "raw": device,
        }
