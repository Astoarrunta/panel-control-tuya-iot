"""
Script de descubrimiento: lista tus dispositivos Fluidra y todos sus
componentes con su valor actual. Úsalo UNA VEZ para identificar qué
component_id corresponde al modo y a la temperatura en tu Eco Elyo
concreto, antes de usar el servicio HTTP para controlarlo.

Uso:
    export FLUIDRA_USERNAME="tu_email@ejemplo.com"
    export FLUIDRA_PASSWORD="tu_password"
    python discover.py
"""

from __future__ import annotations

import json
import os
import sys

from fluidra_client import FluidraAPIError, FluidraAuthError, FluidraClient


def main() -> int:
    username = os.environ.get("FLUIDRA_USERNAME")
    password = os.environ.get("FLUIDRA_PASSWORD")

    if not username or not password:
        print("Define FLUIDRA_USERNAME y FLUIDRA_PASSWORD como variables de entorno.")
        return 1

    client = FluidraClient(username, password)

    print(f"Autenticando como {username}…")
    try:
        client.login()
    except FluidraAuthError as exc:
        print(f"❌ Login fallido: {exc}")
        return 1
    print("✅ Login correcto.\n")

    try:
        devices = client.list_devices()
    except FluidraAPIError as exc:
        print(f"❌ Error listando dispositivos: {exc}")
        return 1

    if not devices:
        print("No se ha encontrado ningún dispositivo vinculado a esta cuenta.")
        return 0

    for device in devices:
        print("=" * 70)
        print(f"Dispositivo: {device['name']}  (id={device['id']})")
        print(f"  Modelo:      {device.get('model')}")
        print(f"  Tipo:        {device.get('type')}")
        print(f"  Serie:       {device.get('serial_number')}")
        print(f"  Conectado:   {device.get('connected')}")
        print(f"  Estado alarma: {device.get('alarm_status')}")
        if device.get("error_code"):
            print(f"  Error: {device['error_code']} - {device.get('error_message')}")

        try:
            components = client.get_device_components(device["id"])
        except FluidraAPIError as exc:
            print(f"  ⚠️  No se pudieron leer los componentes: {exc}")
            continue

        if not components:
            print("  (sin componentes legibles)")
            continue

        print(f"\n  Componentes ({len(components)}):")
        for comp_id, comp in sorted(components.items(), key=lambda kv: str(kv[0])):
            value = comp.get("reportedValue", comp.get("value"))
            extra = {
                k: v
                for k, v in comp.items()
                if k not in ("id", "reportedValue", "value", "raw_data") and v is not None
            }
            print(f"    [{comp_id:>4}] valor actual = {value!r}   {extra if extra else ''}")

        print(
            "\n  💡 Pista: el componente de MODO suele ser un entero pequeño "
            "(0-6) que cambia entre Boost/Smart/Ecosilence al tocarlo desde "
            "la app. El de TEMPERATURA OBJETIVO suele tener un valor entre "
            "10 y 40 con incrementos de 0.5."
        )

    print("\nVolcado completo (JSON) de los dispositivos:")
    print(json.dumps(devices, indent=2, ensure_ascii=False, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
