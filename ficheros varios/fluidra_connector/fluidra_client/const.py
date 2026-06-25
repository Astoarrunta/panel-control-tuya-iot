"""
Constantes de la API privada de Fluidra Connect (usada por la app Fluidra Pool).

IMPORTANTE: Esta es una API NO oficial y NO documentada por Fluidra.
Estos valores se han obtenido mediante ingeniería inversa por parte de la
comunidad (proyectos open-source de integraciones para Home Assistant).
Fluidra puede cambiarlos o bloquearlos en cualquier momento sin previo aviso.
"""

from datetime import timedelta

# ── Endpoints REST ──────────────────────────────────────────────────────────
API_BASE_URL = "https://api.fluidra-emea.com"

API_DEVICES_URL = f"{API_BASE_URL}/generic/devices"
API_CONSUMER_URL = f"{API_BASE_URL}/mobile/consumers/me"
API_USER_PROFILE_URL = f"{API_BASE_URL}/generic/users/me"
API_USER_POOLS_URL = f"{API_BASE_URL}/generic/users/me/pools"
API_POOLS_URL = f"{API_BASE_URL}/generic/pools"
API_POOL_STATUS_URL = f"{API_BASE_URL}/generic/pools/{{pool_id}}/status"

API_DEVICE_COMPONENTS_URL = (
    f"{API_BASE_URL}/generic/devices/{{device_id}}/components?deviceType=connected"
)
API_DEVICE_UICONFIG_URL = (
    f"{API_BASE_URL}/generic/devices/{{device_id}}/uiconfig?appId=iaq&deviceType=connected"
)
API_SET_COMPONENT_VALUE_URL = (
    f"{API_BASE_URL}/generic/devices/{{device_id}}/components/{{component_id}}?deviceType=connected"
)

# ── WebSocket (actualizaciones en tiempo real, opcional) ────────────────────
WS_URL = "wss://ws.fluidra-emea.com"
WS_RECONNECT_DELAY = 5
WS_MAX_RECONNECT_ATTEMPTS = 10

# ── AWS Cognito (autenticación de la app móvil) ─────────────────────────────
COGNITO_REGION = "eu-west-1"
COGNITO_POOL_ID = "eu-west-1_OnopMZF9X"
COGNITO_CLIENT_ID = "g3njunelkcbtefosqm9bdhhq1"

TOKEN_REFRESH_THRESHOLD = timedelta(minutes=10)

# ── Rate limiting por defecto ───────────────────────────────────────────────
DEFAULT_API_RATE_LIMIT = 60  # peticiones / minuto
MIN_API_RATE_LIMIT = 10
MAX_API_RATE_LIMIT = 120

# ── Modos de la bomba de calor (componente típico: id 14) ───────────────────
# Mapeo numérico observado en el ecosistema Fluidra/Zodiac/AstralPool.
# El Eco Elyo usa Boost / Smart / Ecosilence; algunos paneles también
# exponen variantes de calefacción/refrigeración si el equipo es reversible.
HEATPUMP_MODES = {
    0: "smart_heating_cooling",
    1: "boost_heating",
    2: "silence_heating",
    3: "boost_cooling",
    4: "smart_cooling",
    5: "silence_cooling",
    6: "off",
}
HEATPUMP_MODES_REVERSE = {v: k for k, v in HEATPUMP_MODES.items()}

# Códigos de error conocidos (no exhaustivo, varía por modelo)
ERROR_CODES = {
    "E001": "Sin flujo de agua detectado",
    "E002": "Error en sensor de temperatura del agua",
    "E003": "Error en sensor de temperatura ambiente",
    "E004": "Alarma de alta presión",
    "E005": "Alarma de baja presión",
    "E006": "Sobrecarga del compresor",
    "E007": "Error en motor del ventilador",
    "E008": "Error en intercambiador de calor",
    "E009": "Error de comunicación",
    "E010": "Error en alimentación",
    "E011": "Error en sensor de descongelación",
    "E012": "Temperatura de agua demasiado baja",
    "E013": "Temperatura de agua demasiado alta",
    "E014": "Error de secuencia de fase",
    "E015": "Error de comunicación del inverter",
    "E016": "Error en interruptor de flujo de agua",
    "W001": "Temperatura ambiente baja",
    "W002": "Modo descongelación activo",
    "W003": "Limpieza de filtro requerida",
    "W004": "Mantenimiento requerido",
    "W005": "Aviso de temperatura de agua alta",
}
