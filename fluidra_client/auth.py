"""
Autenticación contra AWS Cognito para la API de Fluidra Connect.

La app Fluidra Pool usa un User Pool de AWS Cognito como backend de
identidad. Nos autenticamos con el flujo USER_PASSWORD_AUTH (usuario y
contraseña de tu cuenta de Fluidra Pool) y obtenemos un access_token /
id_token que se reenvían en cada llamada a la API REST.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from .const import COGNITO_CLIENT_ID, COGNITO_REGION, TOKEN_REFRESH_THRESHOLD

logger = logging.getLogger("fluidra_client.auth")


class FluidraAuthError(Exception):
    """Error de autenticación contra Fluidra / Cognito."""


@dataclass
class _Tokens:
    access_token: str
    id_token: str
    refresh_token: str
    expiry: datetime


class FluidraAuth:
    """
    Gestiona el ciclo de vida del token de sesión.

    Es thread-safe de forma básica (usa un lock) porque el servicio HTTP
    puede recibir varias peticiones concurrentes que requieran refrescar
    el token.
    """

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self._tokens: Optional[_Tokens] = None
        self._lock = threading.Lock()
        self._client = boto3.client("cognito-idp", region_name=COGNITO_REGION)

    def authenticate(self) -> None:
        """Autentica desde cero contra Cognito (login completo)."""
        with self._lock:
            self._tokens = self._login_sync()

    def ensure_valid_token(self) -> str:
        """
        Devuelve un access_token válido, autenticando o refrescando si
        es necesario. Es la función que debes llamar antes de cada
        petición a la API.
        """
        with self._lock:
            if self._tokens is None:
                self._tokens = self._login_sync()
            elif datetime.now() + TOKEN_REFRESH_THRESHOLD >= self._tokens.expiry:
                logger.debug("Token a punto de caducar, renovando…")
                try:
                    self._tokens = self._refresh_sync(self._tokens.refresh_token)
                except FluidraAuthError:
                    logger.warning("Refresh fallido, reautenticando con usuario/contraseña")
                    self._tokens = self._login_sync()
            return self._tokens.access_token

    def get_auth_headers(self) -> dict:
        """Cabeceras HTTP necesarias para llamar a la API de Fluidra."""
        token = self.ensure_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Estas dos cabeceras adicionales replican lo observado en la
            # app móvil; algunos endpoints las exigen.
            "x-api-key": token,
            "x-access-token": token,
            "User-Agent": "Fluidra/1.0",
        }

    # ── Internos ─────────────────────────────────────────────────────────

    def _login_sync(self) -> _Tokens:
        try:
            logger.info("Autenticando contra Cognito como %s", self.username)
            response = self._client.initiate_auth(
                ClientId=COGNITO_CLIENT_ID,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": self.username,
                    "PASSWORD": self.password,
                },
            )
            result = response["AuthenticationResult"]
            return _Tokens(
                access_token=result["AccessToken"],
                id_token=result["IdToken"],
                refresh_token=result["RefreshToken"],
                expiry=datetime.now() + timedelta(seconds=result["ExpiresIn"]),
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            message = exc.response.get("Error", {}).get("Message", str(exc))
            logger.error("Fallo de autenticación Cognito [%s]: %s", code, message)
            raise FluidraAuthError(f"{code}: {message}") from exc

    def _refresh_sync(self, refresh_token: str) -> _Tokens:
        try:
            response = self._client.initiate_auth(
                ClientId=COGNITO_CLIENT_ID,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={"REFRESH_TOKEN": refresh_token},
            )
            result = response["AuthenticationResult"]
            return _Tokens(
                access_token=result["AccessToken"],
                id_token=result.get("IdToken", self._tokens.id_token if self._tokens else ""),
                refresh_token=refresh_token,  # Cognito no siempre devuelve uno nuevo
                expiry=datetime.now() + timedelta(seconds=result["ExpiresIn"]),
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            message = exc.response.get("Error", {}).get("Message", str(exc))
            raise FluidraAuthError(f"{code}: {message}") from exc
