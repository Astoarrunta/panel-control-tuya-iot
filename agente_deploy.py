"""
Agente de Despliegue - Panel Control Tuya Smart IoT V2.0
=========================================================
Detecta cambios en el repositorio local y guía al usuario
a través del proceso de actualización en GitHub y PythonAnywhere.

Uso: python agente_deploy.py
"""

import subprocess
import sys
import os

# Archivos cuya modificación requiere Reload en PythonAnywhere
ARCHIVOS_REQUIEREN_RELOAD = ["servidor.py"]

# Colores ANSI para la consola de Windows (requiere Win10+)
VERDE  = "\033[92m"
AMARILLO = "\033[93m"
ROJO   = "\033[91m"
CYAN   = "\033[96m"
BLANCO = "\033[97m"
RESET  = "\033[0m"
NEGRITA = "\033[1m"


def ejecutar(cmd):
    """Ejecuta un comando y retorna su salida como texto."""
    resultado = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return resultado.stdout.strip(), resultado.returncode


def obtener_cambios():
    """Obtiene la lista de archivos modificados, añadidos o eliminados."""
    salida, _ = ejecutar(["git", "status", "--porcelain"])
    if not salida:
        return []
    
    cambios = []
    for linea in salida.splitlines():
        estado = linea[:2].strip()
        archivo = linea[3:].strip()
        cambios.append((estado, archivo))
    return cambios


def necesita_reload(cambios):
    """Determina si algún cambio requiere hacer Reload en PythonAnywhere."""
    archivos_cambiados = [archivo for _, archivo in cambios]
    return any(req in archivos_cambiados for req in ARCHIVOS_REQUIEREN_RELOAD)


def mostrar_cambios(cambios):
    """Muestra la lista de archivos con cambios de forma legible."""
    simbolos = {
        "M": (AMARILLO, "✏️  Modificado"),
        "A": (VERDE,    "➕ Añadido"),
        "D": (ROJO,     "🗑️  Eliminado"),
        "?": (CYAN,     "🆕 Nuevo"),
        "R": (CYAN,     "🔄 Renombrado"),
    }
    print(f"\n{NEGRITA}Archivos con cambios:{RESET}")
    for estado, archivo in cambios:
        color, etiqueta = simbolos.get(estado[0], (BLANCO, f"[{estado}]"))
        print(f"  {color}{etiqueta}{RESET}: {archivo}")


def preguntar(pregunta):
    """Muestra una pregunta y espera respuesta s/n."""
    while True:
        respuesta = input(f"\n{NEGRITA}{pregunta} (s/n): {RESET}").strip().lower()
        if respuesta in ("s", "si", "sí", "y", "yes"):
            return True
        if respuesta in ("n", "no"):
            return False
        print(f"  {AMARILLO}Por favor responde 's' o 'n'.{RESET}")


def main():
    # Habilitar colores ANSI en Windows
    os.system("color")

    print(f"\n{NEGRITA}{CYAN}{'='*52}")
    print(f"  🚀 Agente de Despliegue - Tuya Smart IoT V2.0")
    print(f"{'='*52}{RESET}")

    # 1. Detectar cambios
    cambios = obtener_cambios()

    if not cambios:
        print(f"\n{VERDE}✅ No hay cambios pendientes. El repositorio está actualizado.{RESET}\n")
        sys.exit(0)

    # 2. Mostrar cambios encontrados
    print(f"\n{AMARILLO}⚠️  Se han detectado {len(cambios)} archivo(s) con cambios:{RESET}")
    mostrar_cambios(cambios)

    # 3. Preguntar si actualizar GitHub
    if not preguntar("¿Deseas subir estos cambios a GitHub?"):
        print(f"\n{AMARILLO}⏸️  Operación cancelada. Los cambios quedan pendientes en local.{RESET}\n")
        sys.exit(0)

    # 4. Pedir mensaje de commit
    print(f"\n{BLANCO}Escribe una descripción breve de los cambios:{RESET}")
    print(f"  {CYAN}Ejemplo: 'fix: corregido estado del aire acondicionado'{RESET}")
    mensaje = input(f"  > ").strip()
    if not mensaje:
        mensaje = "update: cambios varios"

    # 5. Ejecutar el .bat de deploy
    print(f"\n{CYAN}⏳ Ejecutando deploy a GitHub...{RESET}")
    bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Actualizacion_github.bat")
    resultado = subprocess.run(["cmd", "/c", bat_path, mensaje], text=True, encoding="utf-8", errors="replace")

    if resultado.returncode != 0:
        print(f"\n{ROJO}❌ El deploy falló. Revisa los mensajes de error anteriores.{RESET}\n")
        sys.exit(1)

    # 6. Mostrar instrucciones para PythonAnywhere
    reload_necesario = necesita_reload(cambios)
    
    print(f"\n{VERDE}{NEGRITA}{'='*52}")
    print(f"  ✅ GitHub actualizado correctamente!")
    print(f"{'='*52}{RESET}")
    print(f"\n{NEGRITA}📋 Ahora actualiza PythonAnywhere:{RESET}")
    print(f"\n  1. Abre la consola {CYAN}Bash{RESET} de PythonAnywhere")
    print(f"     👉 https://www.pythonanywhere.com/consoles/")
    print(f"\n  2. Ejecuta este comando:")
    print(f"\n     {VERDE}cd /home/cristajon && git pull{RESET}")

    if reload_necesario:
        print(f"\n  3. {AMARILLO}⚠️  Has modificado 'servidor.py'.{RESET}")
        print(f"     Debes hacer {NEGRITA}Reload{RESET} en la pestaña Web de PythonAnywhere:")
        print(f"     👉 https://www.pythonanywhere.com/web_app_setup/")
    else:
        print(f"\n  3. {VERDE}✅ No hace falta Reload.{RESET}")
        print(f"     Recarga el navegador con {NEGRITA}Ctrl+F5{RESET} para ver los cambios.")

    print()


if __name__ == "__main__":
    main()
