# Conector local Fluidra Pool (Eco Elyo)

Cliente Python + servicio HTTP local para controlar tu bomba de calor
**Eco Elyo (AstralPool / Fluidra)** desde tu propia aplicación privada,
sin pasar por la app móvil oficial.

## ⚠️ Aviso importante

Fluidra **no publica una API pública ni un MCP oficial**. Este conector
usa la misma API privada que usa la app móvil "Fluidra Pool"
(`api.fluidra-emea.com` + AWS Cognito), obtenida mediante ingeniería
inversa por la comunidad de Home Assistant. Esto implica:

- Puede dejar de funcionar si Fluidra cambia el backend, sin previo aviso.
- Estás usando tus propias credenciales de la cuenta Fluidra Pool — trátalas
  como cualquier contraseña sensible (usa el `.env`, no las metas en
  código ni en repos públicos).
- Conviene un uso razonable (rate limiting incluido por defecto) para no
  arriesgar el bloqueo de tu cuenta.
- Es un proyecto para uso personal/privado, no para redistribuir como
  producto.

## Estructura

```
fluidra_connector/
├── fluidra_client/        # Librería cliente (puedes importarla directamente)
│   ├── __init__.py
│   ├── auth.py            # Login/refresh contra AWS Cognito
│   ├── client.py          # Llamadas a la API REST de Fluidra
│   └── const.py           # Endpoints, modos, códigos de error
├── server.py              # Servicio HTTP local (FastAPI) — esto es lo que consume tu app
├── discover.py            # Script CLI para inspeccionar tus dispositivos/componentes reales
├── requirements.txt
└── .env.example
```

## Instalación

```bash
cd fluidra_connector
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edita .env con tu email y contraseña de la app Fluidra Pool
```

## Paso 1 — Descubre tus componentes reales (hazlo una vez)

Cada modelo/firmware numera los componentes (sensores y controles) de
forma distinta. Antes de controlar nada, identifica qué `component_id`
corresponde al **modo** y a la **temperatura objetivo** en tu Eco Elyo:

```bash
export FLUIDRA_USERNAME="tu_email@ejemplo.com"
export FLUIDRA_PASSWORD="tu_password"
python discover.py
```

Esto imprime todos tus dispositivos y, para cada uno, la lista completa
de componentes con su valor actual. Pistas para identificarlos:

- **Modo**: un entero pequeño (0–6) que cambia si tocas Boost/Smart/Ecosilence
  desde la app oficial mientras tienes `discover.py` corriendo en bucle.
- **Temperatura objetivo**: un valor decimal entre 10 y 40, con pasos de 0.5.

Por defecto el código asume `component_id=14` para el modo y
`component_id=1` para la temperatura (valores típicos vistos en el
ecosistema Fluidra/Zodiac), pero **verifícalo con tu equipo real** — se
pasan como parámetro en cada llamada, así que es fácil ajustarlo.

## Paso 2 — Levanta el servicio HTTP local

```bash
# Con las variables de entorno ya exportadas (ver arriba):
uvicorn server:app --host 127.0.0.1 --port 8077
```

Documentación interactiva automática en `http://127.0.0.1:8077/docs`.

## Uso desde tu aplicación privada

| Acción | Método | Endpoint |
|---|---|---|
| Login manual (si no usaste variables de entorno) | POST | `/login` |
| Listar dispositivos | GET | `/devices` |
| Detalle de un dispositivo | GET | `/devices/{device_id}` |
| Ver todos los componentes/sensores | GET | `/devices/{device_id}/components` |
| Cambiar modo (Smart/Boost/Silence/Off) | POST | `/devices/{device_id}/mode` |
| Cambiar temperatura objetivo | POST | `/devices/{device_id}/temperature` |
| Escribir un componente cualquiera | POST | `/devices/{device_id}/components/{component_id}` |
| Estado del servicio | GET | `/health` |

### Ejemplos `curl`

```bash
# Listar dispositivos
curl http://127.0.0.1:8077/devices

# Cambiar a modo "Smart"
curl -X POST http://127.0.0.1:8077/devices/TU_DEVICE_ID/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "smart_heating_cooling"}'

# Fijar temperatura objetivo a 28.5°C
curl -X POST http://127.0.0.1:8077/devices/TU_DEVICE_ID/temperature \
  -H "Content-Type: application/json" \
  -d '{"temperature_c": 28.5}'
```

Modos válidos: `smart_heating_cooling`, `boost_heating`, `silence_heating`,
`boost_cooling`, `smart_cooling`, `silence_cooling`, `off`.

## Uso como librería Python (sin el servicio HTTP)

Si prefieres importar el cliente directamente en tu app en vez de pasar
por HTTP:

```python
from fluidra_client import FluidraClient

client = FluidraClient(username="...", password="...")
client.login()

devices = client.list_devices()
device_id = devices[0]["id"]

components = client.get_device_components(device_id)
client.set_heatpump_mode(device_id, "smart_heating_cooling")
client.set_target_temperature(device_id, 27.0)
```

## Créditos

Endpoints y flujo de autenticación basados en el trabajo de ingeniería
inversa de la comunidad de Home Assistant, en particular los proyectos
`Roagert/ha-fluidra-pool` y `foXaCe/Fluidra-pool` (ambos MIT License).
