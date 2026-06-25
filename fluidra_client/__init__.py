"""Cliente no oficial para la API de Fluidra Connect (app Fluidra Pool)."""

from .auth import FluidraAuth, FluidraAuthError
from .client import FluidraAPIError, FluidraClient

__all__ = ["FluidraClient", "FluidraAPIError", "FluidraAuth", "FluidraAuthError"]
