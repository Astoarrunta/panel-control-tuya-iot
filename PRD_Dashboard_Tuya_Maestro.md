# PRD Maestro: Dashboard Domótico Tuya (Proyecto Canvas)

## 1. Resumen Ejecutivo
Dashboard de telemetría y control para dispositivos Tuya, diseñado para centralizar información dispersa en una interfaz única ("Single Pane of Glass"). El sistema opera como un middleware que conecta con la API Cloud de Tuya y presenta la información de manera visual, elegante y eficiente en un entorno web local.

## 2. Ecosistema Técnico (Estado Actual)
- **Backend:** Flask (Python 3).
- **Comunicación:** `tinytuya` (Cloud API).
- **Orquestación:** Script `run_app.bat` para automatizar el levantamiento del entorno de desarrollo.
- **Frontend:** Estructura monolítica actual (necesita refactorización hacia MVC).

## 3. Configuración y Credenciales (Deuda Técnica)
- **Estado:** Credenciales hardcodeadas en `servidor.py`.
- **Plan de Mejora:** Migración inminente a variables de entorno (.env) para asegurar el repositorio.
- **IDs de Dispositivos (Hardcoded):**
    - `ID_CONSUMO_GENERAL`: `bf4ef15c37bf6c53e8dbwc`
    - `ID_THERMOSTAT`: `4006843184cca88954c8`
    - `ID_AGUA_PISCINA`: `bff1999b63ffd12874bhan`
    - `ID_RELOJ_PISCINA`: `bf3b6906e261e6d994hgg8`

## 4. Especificaciones del Sistema de Diseño (UI/UX)
- **Estilo:** Dark Mode + Glassmorphism.
- **Grid:** Simétrico (Cards iguales).
- **Visualización:**
    - *Tarjetas:* `rgba(255, 255, 255, 0.05)` con `backdrop-filter: blur(10px)`.
    - *Alertas Dinámicas:*
        - Potencia > 4000W → `Borde: Rojo (#ef4444)`
        - Temp > 30°C → `Icono: Naranja (#f97316)`
        - Temp < 10°C → `Icono: Azul (#38bdf8)`

## 5. Referencia de Archivos (Para el Agente)

### A. Ejecución: `run_app.bat`
El script de arranque debe mantenerse en la raíz. Su función es iniciar el servidor y abrir el navegador en `localhost:5000`.

### B. Lógica: `servidor.py`
El núcleo del proyecto. Todo futuro agente debe respetar la estructura de rutas:
- `@app.route('/api/data')`: Punto de entrada para la telemetría (JSON).
- Integración `tinytuya` existente: Mantener la lógica de conversión `Valor / 10` (Consumo) y `Valor / 2.0` (Temperatura).

## 6. Roadmap de Desarrollo
1. **Fase de Refactorización:** Separar `HTML/CSS/JS` del `servidor.py`. Crear directorio `static/` y `templates/`.
2. **Fase de Funcionalidad:** Implementar `POST` endpoints en `servidor.py` para controlar el estado de la piscina (ON/OFF).
3. **Fase de Datos:** Implementar base de datos SQLite para persistencia y logs.
4. **Fase de Estabilidad:** Implementar manejo de errores robusto en la conexión a la Cloud de Tuya.
