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
    - `ID_SMART_IR` (Padre de mandos IR): `bfb88b2cabd1a639995kgy`
    - `ID_AIRE_CRIS` (AC Inteligente Tuya): `bf8404d4e90f7cce02gzsq`
    - `ID_AIRE_NOCHE` (Mando DIY copiado): `bfa3ae255f54aa56abxm6g`

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
4. **Fase de Estabilidad:** Implementar manejo de errores robusto en la conexión a la Cloud de Tuya.
5. **Seguridad Integrada:** Añadida confirmación en Javascript para encendido de bomba de piscina (evita clics accidentales).

## 7. Lecciones Técnicas y Resolución de Problemas (Troubleshooting)

### A. Error "sign invalid" (Código 1004 / 911)
Si Tuya rechaza las peticiones (ya sea en local o en PythonAnywhere) suele deberse a dos factores:
- **Desincronización de Reloj:** Tuya requiere que la petición (`time.time()`) coincida con el servidor de internet con margen < 5 minutos.
- **Renovación del Free Trial (Tuya IoT Platform):** Al extender la licencia de desarrollador gratuita, la plataforma **regenera automáticamente el "Access Secret"**. Es imperativo actualizar el archivo `.env` inmediatamente tras aprobarse la extensión.

### B. Conflicto de caché (`tinytuya.json`)
La librería `tinytuya` crea un caché local. En despliegues hacia PythonAnywhere:
- `.env` y `tinytuya.json` están en `.gitignore` por seguridad.
- Al cambiar el `TUYA_API_SECRET`, es fundamental **borrar el archivo `tinytuya.json` viejo en el servidor Cloud**, de lo contrario Python entrará en conflicto firmando con un token caducado e ignorando el `.env` actualizado.

### C. Contexto WSGI en PythonAnywhere
El despliegue con GitHub requiere verificar que el archivo de configuración WSGI (`/var/www/..._wsgi.py`) apunte a la subcarpeta del repositorio (`App_PanelControl_TuyaSmart_ioT/tuya smart/proyecto_V2.0/`) como `project_home`, y no a la raíz del usuario.
