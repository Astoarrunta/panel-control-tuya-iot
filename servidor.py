import os
import sys
import argparse
import signal
import time
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_basicauth import BasicAuth
from dotenv import load_dotenv
import tinytuya
# Importación defensiva de fluidra_client (evita caídas si falta boto3 u otra dependencia)
try:
    from fluidra_client import FluidraClient, FluidraAPIError, FluidraAuthError
except ImportError as e:
    print(f"[ADVERTENCIA] No se pudo importar fluidra_client (comprobar boto3): {e}")
    FluidraClient = None
    # Definimos clases dummy para evitar errores de referencia en el código
    class FluidraAPIError(Exception): pass
    class FluidraAuthError(Exception): pass

# 1. Configuración de Entorno (Ruta absoluta para asegurar carga en WSGI/PythonAnywhere)
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, '.env')) 

# 2. Argumentos de ejecución
# Usamos parse_known_args para ignorar argumentos del servidor WSGI (PythonAnywhere)
parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['local', 'cloud'], default='local')
args, _ = parser.parse_known_args()

# Detección inteligente de modo
# APP_MODE define el modo de ejecución en local o en cloud
MODE = os.getenv('APP_MODE', args.mode) 
print(f"--- Iniciando Sistema en MODO: {MODE.upper()} ---")

# 3. Configuración de la App
app = Flask(__name__)
CORS(app)
app.config['BASIC_AUTH_USERNAME'] = os.getenv('BASIC_AUTH_USER', 'admin')
app.config['BASIC_AUTH_PASSWORD'] = os.getenv('BASIC_AUTH_PASS', 'admin123')
basic_auth = BasicAuth(app)

# 4. Configuración Tuya Cloud
API_KEY = os.getenv('TUYA_API_KEY')
API_SECRET = os.getenv('TUYA_API_SECRET')
API_REGION = os.getenv('TUYA_REGION', 'eu')

# Validación defensiva: avisar en log si faltan credenciales
if not API_KEY or not API_SECRET:
    print("[ERROR CRITICO] Faltan variables de entorno TUYA_API_KEY o TUYA_API_SECRET")
    print(f"[DEBUG] API_KEY presente: {bool(API_KEY)}, API_SECRET presente: {bool(API_SECRET)}")
    print(f"[DEBUG] Variables de entorno disponibles: {list(os.environ.keys())}")

try:
    cloud = tinytuya.Cloud(apiRegion=API_REGION, apiKey=API_KEY, apiSecret=API_SECRET)
    print(f"[OK] Tuya Cloud inicializada correctamente (Region: {API_REGION})")
except Exception as e:
    print(f"[ERROR] Fallo al iniciar Tuya Cloud: {e}")
    cloud = None

# Identificadores de los dispositivos domóticos Tuya
DEVICES = {
    "consumo": "bf4ef15c37bf6c53e8dbwc",
    "termostato": "4006843184cca88954c8",
    "agua": "bff1999b63ffd12874bhan",
    "reloj": "bf3b6906e261e6d994hgg8",
    "aire": "bf8404d4e90f7cce02gzsq"
}

# 5. Configuración Fluidra
FLUIDRA_USERNAME = os.getenv('FLUIDRA_USERNAME')
FLUIDRA_PASSWORD = os.getenv('FLUIDRA_PASSWORD')
FLUIDRA_DEVICE_ID = os.getenv('FLUIDRA_DEVICE_ID', 'LG25363958')

_fluidra_client = None
_fluidra_init_error = None
_fluidra_cache = {"data": None, "timestamp": 0}

def get_fluidra_client():
    """Inicializa de forma perezosa el cliente de Fluidra."""
    global _fluidra_client, _fluidra_init_error
    if _fluidra_client is None:
        if FluidraClient is None:
            _fluidra_init_error = "Librería fluidra_client o boto3 no importada en el servidor"
            return None
        if not FLUIDRA_USERNAME or not FLUIDRA_PASSWORD:
            _fluidra_init_error = "Variables de entorno FLUIDRA_USERNAME o FLUIDRA_PASSWORD no encontradas en el .env"
            return None
        try:
            _fluidra_client = FluidraClient(FLUIDRA_USERNAME, FLUIDRA_PASSWORD)
            _fluidra_client.login()
            _fluidra_init_error = None
            print("[OK] Fluidra Client inicializado correctamente")
        except Exception as e:
            _fluidra_init_error = f"Error al conectar/autenticar con Fluidra: {str(e)}"
            print(f"[ERROR] Fallo al iniciar Fluidra Client: {e}")
            _fluidra_client = None
    return _fluidra_client

def get_fluidra_data():
    """Obtiene y cachea los datos de telemetría de Fluidra."""
    now = time.time()
    # Cacheamos durante 10 segundos para no saturar la API
    if _fluidra_cache["data"] and (now - _fluidra_cache["timestamp"] < 10):
        return _fluidra_cache["data"]
        
    client = get_fluidra_client()
    if not client:
        return {"error": _fluidra_init_error or "Fluidra no configurado"}
        
    try:
        components = client.get_device_components(FLUIDRA_DEVICE_ID)
        device_info = client.get_device(FLUIDRA_DEVICE_ID)
        
        comp_13 = components.get("13", {})  # Encendido/Apagado
        comp_14 = components.get("14", {})  # Modo (0-6)
        comp_15 = components.get("15", {})  # Temp Objetivo (setpoint)
        comp_19 = components.get("19", {})  # Temp Agua (piscina)
        comp_67 = components.get("67", {})  # Temp Aire
        comp_0 = components.get("0", {})    # Horas de funcionamiento
        
        power_val = comp_13.get("reportedValue", comp_13.get("value"))
        mode_val = comp_14.get("reportedValue", comp_14.get("value"))
        target_temp_val = comp_15.get("reportedValue", comp_15.get("value"))
        water_temp_val = comp_19.get("reportedValue", comp_19.get("value"))
        air_temp_val = comp_67.get("reportedValue", comp_67.get("value"))
        hours_val = comp_0.get("reportedValue", comp_0.get("value"))
        
        is_on = power_val == 1 if power_val is not None else False
        mode_num = int(mode_val) if mode_val is not None else 0
        target_temp = float(target_temp_val) / 10.0 if target_temp_val is not None else 0.0
        water_temp = float(water_temp_val) / 10.0 if water_temp_val is not None else 0.0
        air_temp = float(air_temp_val) / 10.0 if air_temp_val is not None else 0.0
        running_hours = int(hours_val) if hours_val is not None else 0
        
        res = {
            "connected": device_info.get("connected") if device_info else False,
            "alarm_status": device_info.get("alarm_status") if device_info else "normal",
            "alarm_count": device_info.get("alarm_count") if device_info else 0,
            "error_code": device_info.get("error_code") if device_info else None,
            "error_message": device_info.get("error_message") if device_info else None,
            "power": is_on,
            "mode": mode_num,
            "target_temp": target_temp,
            "water_temp": water_temp,
            "air_temp": air_temp,
            "running_hours": running_hours,
            "name": device_info.get("name") if device_info else "Eco Elyo"
        }
        _fluidra_cache["data"] = res
        _fluidra_cache["timestamp"] = now
        return res
    except Exception as e:
        print(f"[ERROR] Error al leer datos de la API de Fluidra: {e}")
        if _fluidra_cache["data"]:
            return _fluidra_cache["data"]
        return {"error": str(e)}

# 6. Rutas de la Aplicación
@app.route('/')
def home():
    # Renderizar la vista landing page pasando el modo de ejecución al template
    return render_template('landing.html', mode=MODE)

@app.route('/control')
@basic_auth.required
def index():
    # Renderizar la vista del panel de control pasando variables a Jinja2
    return render_template(
        'dashboard.html', 
        mode=MODE, 
        mode_label=MODE.upper(),
        id_agua=DEVICES["agua"], 
        id_reloj=DEVICES["reloj"],
        id_aire=DEVICES["aire"]
    )

@app.route('/api/data')
@basic_auth.required
def get_data():
    if not cloud: return jsonify({"error": "Cloud no inicializada"}), 500
    res_t = cloud.getstatus(DEVICES["termostato"])
    res_p = cloud.getstatus(DEVICES["consumo"])
    res_ap = cloud.getstatus(DEVICES["agua"])
    res_rp = cloud.getstatus(DEVICES["reloj"])
    
    # Consultar el estado del Aire Acondicionado virtual en Tuya Cloud (API Infrarrojos)
    res_a = cloud.cloudrequest(f"/v2.0/infrareds/bfb88b2cabd1a639995kgy/remotes/{DEVICES['aire']}/ac/status", action="GET")

    t_data = {"switch": False, "temp_current": 0, "temp_set": 0}
    res_t_result = res_t.get('result', []) if isinstance(res_t, dict) else []
    for i in res_t_result:
        if i['code'] == 'switch': t_data["switch"] = i['value']
        if i['code'] == 'upper_temp': t_data["temp_current"] = i['value'] / 2.0
        if i['code'] == 'temp_set': t_data["temp_set"] = i['value'] / 2.0

    p_data = {"w": 0, "v": 0}
    res_p_result = res_p.get('result', []) if isinstance(res_p, dict) else []
    for i in res_p_result:
        if i['code'] == 'cur_power': p_data["w"] = i['value'] / 10
        if i['code'] == 'cur_voltage': p_data["v"] = i['value'] / 10

    piscina_data = {"agua": False, "reloj": False}
    res_ap_result = res_ap.get('result', []) if isinstance(res_ap, dict) else []
    for i in res_ap_result:
        if i['code'] == 'switch_1': piscina_data["agua"] = i['value']
    res_rp_result = res_rp.get('result', []) if isinstance(res_rp, dict) else []
    for i in res_rp_result:
        if i['code'] == 'switch': piscina_data["reloj"] = i['value']

    # Procesar estado del aire acondicionado
    aire_data = {"power": False, "temp": 24, "mode": 0, "wind": 0}
    if isinstance(res_a, dict) and res_a.get('success', False):
        result_a = res_a.get('result', {})
        aire_data["power"] = result_a.get('power') == '1'
        aire_data["temp"] = int(result_a.get('temp', 24))
        aire_data["mode"] = int(result_a.get('mode', 0))
        aire_data["wind"] = int(result_a.get('wind', 0))

    # Obtener estado de Fluidra
    fluidra_data = get_fluidra_data()

    return jsonify({
        "thermostat": t_data, 
        "pow": p_data, 
        "piscina": piscina_data,
        "aire": aire_data,
        "fluidra": fluidra_data
    })

@app.route('/api/toggle', methods=['POST'])
@basic_auth.required
def toggle():
    data = request.json
    try:
        code = 'switch_1' if data['id'] == DEVICES["agua"] else 'switch'
        cmd_payload = {
            "commands": [
                {"code": code, "value": data['state']}
            ]
        }
        res = cloud.sendcommand(data['id'], cmd_payload)
        
        if isinstance(res, dict) and res.get('success', False):
            return jsonify({"status": "success"})
        else:
            error_msg = res.get('msg', 'Error desconocido') if isinstance(res, dict) else 'Respuesta no válida'
            return jsonify({"status": "error", "message": error_msg})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/command', methods=['POST'])
@basic_auth.required
def send_command():
    data = request.json
    try:
        remote_id = data['id']
        code = data['code']
        value = data['value']
        
        infrared_id = "bfb88b2cabd1a639995kgy"
        
        if code == 'power':
            value = 1 if bool(value) else 0
        else:
            value = int(value)
            
        path = f"/v2.0/infrareds/{infrared_id}/air-conditioners/{remote_id}/command"
        payload = {
            "code": code,
            "value": value
        }
        
        res = cloud.cloudrequest(path, action="POST", post=payload)
        
        if isinstance(res, dict) and res.get('success', False):
            return jsonify({"status": "success"})
        else:
            error_msg = res.get('msg', 'Error desconocido') if isinstance(res, dict) else 'Respuesta no válida'
            return jsonify({"status": "error", "message": error_msg})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/fluidra/command', methods=['POST'])
@basic_auth.required
def fluidra_command():
    return jsonify({
        "status": "error", 
        "message": "Los comandos para la bomba de calor están desactivados temporalmente (Modo Lectura)."
    }), 403

@app.route('/api/trigger_aire_custom', methods=['POST'])
@basic_auth.required
def trigger_aire_custom():
    data = request.json
    key_id = data.get('key', '1')
    
    # Mapa de botones del dashboard a escenas Tuya "Tap to Run"
    # home_id: 25900318 (hogar Ruso en Tuya Smart)
    HOME_ID = 25900318
    SCENE_MAP = {
        '1': {'id': 'waVuzAMkDJI2RKen', 'name': 'Modo Noche'},
        # Añadir aquí el scene_id de "Apagar LED" cuando se cree por separado
    }
    
    scene = SCENE_MAP.get(key_id)
    if not scene:
        return jsonify({"status": "error", "message": f"No hay escena configurada para el boton {key_id}"})
    
    try:
        # Lanzar la escena "Tap to Run" via API v1.0 homes
        path = f"/v1.0/homes/{HOME_ID}/scenes/{scene['id']}/trigger"
        res = cloud.cloudrequest(path, action="POST")
        
        if isinstance(res, dict) and res.get('success', False):
            return jsonify({"status": "success", "scene": scene['name']})
        else:
            error_msg = res.get('msg', 'Error desconocido') if isinstance(res, dict) else 'Respuesta no valida'
            return jsonify({"status": "error", "message": error_msg})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# Endpoint de actualización GitHub (solo disponible en modo LOCAL)
@app.route('/api/deploy', methods=['POST'])
def deploy():
    if MODE != 'local':
        return jsonify({"status": "error", "message": "Solo disponible en modo local"}), 403
    
    data = request.json
    msg = data.get('message', 'update: cambios varios')
    
    try:
        import subprocess
        # Archivos cuya modificación requiere Reload en PythonAnywhere
        REQUIEREN_RELOAD = ["servidor.py"]
        
        # Detectar si hay cambios y qué archivos se modificaron
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True
        )
        archivos_cambiados = [l[3:].strip() for l in status_res.stdout.splitlines()]
        reload_needed = any(r in archivos_cambiados for r in REQUIEREN_RELOAD)
        
        # Ejecutar git add + commit + push
        salida = ""
        for cmd in [
            ["git", "add", "."],
            ["git", "commit", "-m", msg],
            ["git", "push", "origin", "main"]
        ]:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            salida += res.stdout + res.stderr
            if res.returncode != 0 and "nothing to commit" not in res.stdout:
                return jsonify({"status": "error", "output": salida})
        
        return jsonify({"status": "success", "output": salida, "reload_needed": reload_needed})
    except Exception as e:
        return jsonify({"status": "error", "output": str(e)})

# Ruta secreta para ordenar el apagado del proceso CMD
@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    print("--- Recibida orden de apagado. Cerrando CMD... ---")
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({"status": "shutdown"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)