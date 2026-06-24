"""
Comprueba el dispositivo Tuya usando el SDK OFICIAL (tuya-connector-python).
Evita cualquier error de firma hecha a mano.

Instalación:
    pip install tuya-connector-python

Uso:
    python check_tuya_device_sdk.py
"""
from tuya_connector import TuyaOpenAPI

ACCESS_ID = "8sx5tcyqwpkjsynt3gdd"
ACCESS_SECRET = "798a433b21ba481c8e6d8683d6a6687a"
DEVICE_ID = "bf4ef15c37bf6c53e8dbwc"
API_ENDPOINT = "https://openapi.tuyaeu.com"  # región eu

openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_SECRET)

print("1) Conectando y obteniendo token...")
connect_result = openapi.connect()
print(connect_result)

if not connect_result.get("success"):
    print("\n❌ Fallo de conexión/token. Revisa el mensaje de error arriba.")
    exit(1)

print("\n2) Info del dispositivo...")
info = openapi.get(f"/v1.0/devices/{DEVICE_ID}")
print(info)

print("\n3) Estado (data points) del dispositivo...")
status = openapi.get(f"/v1.0/devices/{DEVICE_ID}/status")
print(status)
