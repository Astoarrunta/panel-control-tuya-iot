"""
Servicio HTTP local que envuelve fluidra_client en una pequeña API REST,
pensada para que tu aplicación privada la consuma desde localhost.

Arranque:
    uvicorn server:app --host 127.0.0.1 --port 8077

Configura las credenciales mediante variables de entorno (ver .env.example)
o pásalas en el primer login vía POST /login.

Endpoints:
    POST   /login                                  Autentica contra Fluidra
    GET    /devices                                Lista dispositivos
    GET    /devices/{device_id}                    Detalle de un dispositivo
    GET    /devices/{device_id}/components          Componentes/sensores
    POST   /devices/{device_id}/mode                Cambia el modo (Smart/Boost/...)
    POST   /devices/{device_id}/temperature          Cambia la temperatura objetivo
    POST   /devices/{device_id}/components/{id}      Escritura genérica de componente
    GET    /health                                  Estado del servicio
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from fluidra_client import FluidraAPIError, FluidraAuthError, FluidraClient
from fluidra_client.const import HEATPUMP_MODES_REVERSE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fluidra_server")

app = FastAPI(
    title="Conector local Fluidra Pool",
    description="API REST local (no oficial) para tu bomba de calor Eco Elyo / equipos Fluidra.",
    version="1.0.0",
)

_client: Optional[FluidraClient] = None


def get_client() -> FluidraClient:
    global _client
    if _client is None:
        username = os.environ.get("FLUIDRA_USERNAME")
        password = os.environ.get("FLUIDRA_PASSWORD")
        if not username or not password:
            raise HTTPException(
                status_code=401,
                detail=(
                    "No hay sesión activa. Llama a POST /login con tus "
                    "credenciales, o define FLUIDRA_USERNAME/FLUIDRA_PASSWORD "
                    "como variables de entorno antes de arrancar el servicio."
                ),
            )
        _client = FluidraClient(username, password)
        try:
            _client.login()
        except FluidraAuthError as exc:
            _client = None
            raise HTTPException(status_code=401, detail=f"Login fallido: {exc}") from exc
    return _client


# ── Modelos de petición ──────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class ModeRequest(BaseModel):
    mode: str  # smart_heating_cooling | boost_heating | silence_heating | ...
    mode_component_id: int = 14


class TemperatureRequest(BaseModel):
    temperature_c: float
    temp_component_id: int = 1


class ComponentValueRequest(BaseModel):
    value: Any


# ── Manejo de errores común ──────────────────────────────────────────────


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except FluidraAPIError as exc:
        status = exc.status_code or 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except FluidraAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


# ── Endpoints ─────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "authenticated": _client is not None}


@app.post("/login")
def login(body: LoginRequest) -> Dict[str, Any]:
    global _client
    client = FluidraClient(body.username, body.password)
    try:
        client.login()
    except FluidraAuthError as exc:
        raise HTTPException(status_code=401, detail=f"Login fallido: {exc}") from exc
    _client = client
    return {"status": "authenticated"}


@app.get("/devices")
def list_devices() -> Dict[str, Any]:
    client = get_client()
    devices = _call(client.list_devices)
    return {"count": len(devices), "devices": devices}


@app.get("/devices/{device_id}")
def get_device(device_id: str) -> Dict[str, Any]:
    client = get_client()
    device = _call(client.get_device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return device


@app.get("/devices/{device_id}/components")
def get_components(device_id: str) -> Dict[str, Any]:
    client = get_client()
    components = _call(client.get_device_components, device_id)
    return {"device_id": device_id, "components": components}


@app.get("/devices/{device_id}/uiconfig")
def get_uiconfig(device_id: str) -> Dict[str, Any]:
    client = get_client()
    return _call(client.get_device_uiconfig, device_id)


@app.post("/devices/{device_id}/mode")
def set_mode(device_id: str, body: ModeRequest) -> Dict[str, Any]:
    if body.mode not in HEATPUMP_MODES_REVERSE:
        valid = ", ".join(HEATPUMP_MODES_REVERSE)
        raise HTTPException(
            status_code=400, detail=f"Modo no válido. Usa uno de: {valid}"
        )
    client = get_client()
    _call(client.set_heatpump_mode, device_id, body.mode, body.mode_component_id)
    return {"status": "ok", "device_id": device_id, "mode": body.mode}


@app.post("/devices/{device_id}/temperature")
def set_temperature(device_id: str, body: TemperatureRequest) -> Dict[str, Any]:
    client = get_client()
    _call(
        client.set_target_temperature,
        device_id,
        body.temperature_c,
        body.temp_component_id,
    )
    return {
        "status": "ok",
        "device_id": device_id,
        "temperature_c": body.temperature_c,
    }


@app.post("/devices/{device_id}/components/{component_id}")
def set_component(device_id: str, component_id: str, body: ComponentValueRequest) -> Dict[str, Any]:
    client = get_client()
    _call(client.set_component_value, device_id, component_id, body.value)
    return {
        "status": "ok",
        "device_id": device_id,
        "component_id": component_id,
        "value": body.value,
    }


@app.get("/user/profile")
def user_profile() -> Dict[str, Any]:
    client = get_client()
    return _call(client.get_user_profile)
