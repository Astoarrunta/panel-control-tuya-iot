"""
Script de inventario completo de dispositivos Tuya.
- Lista TODOS los dispositivos de la cuenta con sus propiedades y DPs actuales.
- Para el IR Hub, también lista los mandos y sus botones aprendidos.
- Guarda el resultado completo en devices.json.
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import tinytuya

load_dotenv()

INFRARED_ID = "bfb88b2cabd1a639995kgy"
OUTPUT_FILE = "devices.json"

cloud = tinytuya.Cloud(
    apiRegion=os.getenv('TUYA_REGION', 'eu'),
    apiKey=os.getenv('TUYA_API_KEY'),
    apiSecret=os.getenv('TUYA_API_SECRET')
)

# ─────────────────────────────────────────────
# 1. Obtener lista base de todos los dispositivos
# ─────────────────────────────────────────────
print("\n[1/3] Obteniendo lista de dispositivos...")
raw_devices = cloud.getdevices()

if not raw_devices or isinstance(raw_devices, dict) and not raw_devices.get('success', True):
    print("Error al obtener dispositivos:", raw_devices)
    exit(1)

print(f"      {len(raw_devices)} dispositivos encontrados.")

# ─────────────────────────────────────────────
# 2. Para cada dispositivo, obtener estado actual (DPs)
# ─────────────────────────────────────────────
print("[2/3] Consultando estado de cada dispositivo...")

inventory = []

for dev in raw_devices:
    dev_id   = dev.get('id', '')
    dev_name = dev.get('name', dev_id)
    category = dev.get('category', '')

    # Obtener estado actual (Data Points)
    status_res = cloud.getstatus(dev_id)
    dps = []
    if isinstance(status_res, dict) and status_res.get('success'):
        dps = status_res.get('result', [])

    entry = {
        "id":           dev_id,
        "name":         dev_name,
        "category":     category,
        "product_name": dev.get('product_name', ''),
        "model":        dev.get('model', ''),
        "mac":          dev.get('mac', ''),
        "ip":           dev.get('ip', ''),
        "online":       dev.get('online', False),
        "dps":          dps,
        "ir_remotes":   []
    }

    print(f"      [{category}] {dev_name} -> {len(dps)} DPs | online={entry['online']}")
    inventory.append(entry)

# ─────────────────────────────────────────────
# 3. Añadir mandos IR y sus botones al Hub infrarrojo
# ─────────────────────────────────────────────
print("[3/3] Consultando mandos del IR Hub...")

remotes_res = cloud.cloudrequest(f'/v1.0/infrareds/{INFRARED_ID}/remotes')

if remotes_res.get('success'):
    remotes = remotes_res.get('result', [])
    print(f"      {len(remotes)} mandos encontrados.")

    # Buscar el hub en el inventario para anidar los mandos
    hub_entry = next((d for d in inventory if d['id'] == INFRARED_ID), None)

    ir_remotes_list = []

    for remote in remotes:
        remote_id   = remote.get('remote_id', '')
        remote_name = remote.get('remote_name', '')
        brand       = remote.get('brand_name', 'N/A')

        # Botones de cada mando
        keys_res = cloud.cloudrequest(
            f'/v1.0/infrareds/{INFRARED_ID}/remotes/{remote_id}/keys'
        )
        key_list = []
        if keys_res.get('success'):
            key_list = keys_res.get('result', {}).get('key_list', [])

        remote_entry = {
            "remote_id":   remote_id,
            "remote_name": remote_name,
            "brand":       brand,
            "category_id": keys_res.get('result', {}).get('category_id', ''),
            "standard":    keys_res.get('result', {}).get('single_air', False),
            "buttons":     [
                {
                    "key_id":       k.get('key_id'),
                    "key":          k.get('key'),
                    "name":         k.get('key_name'),
                    "standard_key": k.get('standard_key', False)
                }
                for k in key_list
            ]
        }

        print(f"        Mando: '{remote_name}' | ID: {remote_id} | {len(key_list)} botones")
        ir_remotes_list.append(remote_entry)

    if hub_entry:
        hub_entry['ir_remotes'] = ir_remotes_list
    else:
        # Si el hub no estaba en la lista de getdevices, lo añadimos aparte
        inventory.append({
            "id":           INFRARED_ID,
            "name":         "IR Hub",
            "category":     "ir_hub",
            "ir_remotes":   ir_remotes_list
        })

# ─────────────────────────────────────────────
# 4. Guardar en devices.json
# ─────────────────────────────────────────────
output = {
    "generated_at": datetime.now().isoformat(),
    "total_devices": len(inventory),
    "devices": inventory
}

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nOK - Inventario guardado en '{OUTPUT_FILE}'")
print(f"  Total dispositivos: {len(inventory)}")
print(f"  Generado: {output['generated_at']}\n")

# ─────────────────────────────────────────────
# 5. Resumen visual en consola
# ─────────────────────────────────────────────
print("=" * 60)
print(f"{'NOMBRE':<30} {'CATEGORIA':<10} {'ONLINE':<8} {'DPS'}")
print("=" * 60)
for d in inventory:
    print(f"{d['name']:<30} {d['category']:<10} {str(d.get('online','')):<8} {len(d.get('dps', []))}")
    if d.get('ir_remotes'):
        for r in d['ir_remotes']:
            print(f"    -> [{r['remote_id'][:20]}] {r['remote_name']} ({len(r['buttons'])} botones)")
print("=" * 60)
