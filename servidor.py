import os
import sys
import argparse
import signal
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_basicauth import BasicAuth
from dotenv import load_dotenv
import tinytuya

# 1. Configuración de Entorno
load_dotenv() 

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

# 6. Rutas de la Aplicación
@app.route('/')
def home():
    # Renderizar la vista landing page desvinculada
    return render_template('landing.html')

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

    return jsonify({
        "thermostat": t_data, 
        "pow": p_data, 
        "piscina": piscina_data,
        "aire": aire_data
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
        
        # El Smart IR es el dispositivo padre: bfb88b2cabd1a639995kgy
        infrared_id = "bfb88b2cabd1a639995kgy"
        
        # Normalizar tipos de datos para infrarrojos de Tuya AC
        # power debe ser 1 o 0 (integer)
        if code == 'power':
            value = 1 if bool(value) else 0
        else:
            value = int(value)
            
        path = f"/v2.0/infrareds/{infrared_id}/air-conditioners/{remote_id}/command"
        payload = {
            "code": code,
            "value": value
        }
        
        # Enviar petición a la API de Infrarrojos de Tuya Cloud
        res = cloud.cloudrequest(path, action="POST", post=payload)
        
        if isinstance(res, dict) and res.get('success', False):
            return jsonify({"status": "success"})
        else:
            error_msg = res.get('msg', 'Error desconocido') if isinstance(res, dict) else 'Respuesta no válida'
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