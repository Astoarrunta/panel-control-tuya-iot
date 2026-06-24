"""
Comprueba el estado de un dispositivo Tuya vía Cloud API.
Requiere: pip install requests

Uso:
    python check_tuya_device.py
"""
import hashlib
import hmac
import time
import requests

# --- Credenciales ---
CLIENT_ID = "8sx5tcyqwpkjsynt3gdd"
CLIENT_SECRET = "798a433b21ba481c8e6d8683d6a6687a"
DEVICE_ID = "bf4ef15c37bf6c53e8dbwc"
REGION = "eu"  # eu / us / cn / in

BASE_URL = f"https://openapi.tuya{REGION}.com"

EMPTY_BODY_SHA256 = hashlib.sha256(b"").hexdigest()


def sign(client_id, secret, t, nonce, method, url, access_token=""):
    string_to_sign = f"{method}\n{EMPTY_BODY_SHA256}\n\n{url}"
    str_to_hash = client_id + access_token + t + nonce + string_to_sign
    return hmac.new(secret.encode(), str_to_hash.encode(), hashlib.sha256).hexdigest().upper()


def get_token():
    t = str(int(time.time() * 1000))
    nonce = ""
    url_path = "/v1.0/token?grant_type=1"
    sign_value = sign(CLIENT_ID, CLIENT_SECRET, t, nonce, "GET", url_path)

    headers = {
        "client_id": CLIENT_ID,
        "sign": sign_value,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "nonce": nonce,
    }
    resp = requests.get(BASE_URL + url_path, headers=headers)
    return resp.json()


def get_device_status(access_token):
    t = str(int(time.time() * 1000))
    nonce = ""
    url_path = f"/v1.0/devices/{DEVICE_ID}/status"
    sign_value = sign(CLIENT_ID, CLIENT_SECRET, t, nonce, "GET", url_path, access_token)

    headers = {
        "client_id": CLIENT_ID,
        "access_token": access_token,
        "sign": sign_value,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "nonce": nonce,
    }
    resp = requests.get(BASE_URL + url_path, headers=headers)
    return resp.json()


def get_device_info(access_token):
    t = str(int(time.time() * 1000))
    nonce = ""
    url_path = f"/v1.0/devices/{DEVICE_ID}"
    sign_value = sign(CLIENT_ID, CLIENT_SECRET, t, nonce, "GET", url_path, access_token)

    headers = {
        "client_id": CLIENT_ID,
        "access_token": access_token,
        "sign": sign_value,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "nonce": nonce,
    }
    resp = requests.get(BASE_URL + url_path, headers=headers)
    return resp.json()


if __name__ == "__main__":
    print("1) Obteniendo token...")
    token_resp = get_token()
    print(token_resp)

    if not token_resp.get("success"):
        print("\n❌ No se pudo obtener el token. Revisa el error 'code'/'msg' arriba.")
        exit(1)

    access_token = token_resp["result"]["access_token"]

    print("\n2) Info del dispositivo...")
    print(get_device_info(access_token))

    print("\n3) Estado (data points) del dispositivo...")
    print(get_device_status(access_token))
