/**
 * Control del Dashboard Domótico Tuya Smart IoT V2.0
 * Lógica asíncrona de telemetría y cambio de estados.
 */

// Actualizar texto de estado de un switch
function updateStatusUI(textId, switchId, isOn) {
    const textEl = document.getElementById(textId);
    const switchEl = document.getElementById(switchId);
    
    // Sincronizar el estado del interruptor deslizante
    if (switchEl) {
        switchEl.checked = isOn;
    }
    
    // Sincronizar el texto informativo y las clases de color
    if (textEl) {
        textEl.innerText = isOn ? "ENCENDIDO" : "APAGADO";
        if (isOn) {
            textEl.classList.remove('off');
            textEl.classList.add('on');
        } else {
            textEl.classList.remove('on');
            textEl.classList.add('off');
        }
    }
}

// Activar o deshabilitar visualmente los controles del Aire Acondicionado
function setAcControlsState(isOn) {
    const wrapper = document.getElementById('ac-controls-wrapper');
    if (!wrapper) return;
    
    if (isOn) {
        // Encendido: quitar sombreado y permitir interacción
        wrapper.classList.remove('disabled-controls');
    } else {
        // Apagado: sombrear y bloquear interacción como en la app móvil
        wrapper.classList.add('disabled-controls');
    }
}

// Acción de cambiar el estado (ON/OFF) de un dispositivo Tuya
async function toggleDevice(deviceId, switchId, textId) {
    const switchEl = document.getElementById(switchId);
    const newState = switchEl.checked;
    
    // Si se está intentando encender el agua de la piscina, pedir confirmación para evitar accidentes
    if (switchId === 'ap-switch' && newState === true) {
        if (!confirm("¿Estás seguro de que deseas encender el motor de Agua de la Piscina?")) {
            switchEl.checked = false; // Revertimos visualmente el estado del switch
            return; // Abortamos la petición a la API
        }
    }
    
    // ActualizarUI inmediatamente para dar sensación de reactividad
    updateStatusUI(textId, switchId, newState);
    
    try {
        const response = await fetch('/api/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: deviceId,
                state: newState
            })
        });
        
        const result = await response.json();
        
        // Si el servidor reporta un error, revertir el estado del interruptor
        if (result.status !== 'success') {
            console.error("Fallo al cambiar estado en la nube de Tuya:", result.message);
            alert("No se pudo conmutar el dispositivo: " + (result.message || "Error desconocido"));
            updateStatusUI(textId, switchId, !newState);
        }
    } catch (error) {
        console.error("Error de comunicación con la API del servidor:", error);
        alert("Error al comunicar con el servidor local. Revertiendo acción.");
        updateStatusUI(textId, switchId, !newState);
    }
}

// Consulta periódica de telemetría (Polling)
async function updateTelemetry() {
    try {
        const response = await fetch('/api/data');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // --- 1. Sincronización de Termostato ---
        const currentTemp = data.thermostat.temp_current;
        const targetTemp = data.thermostat.temp_set;
        const isTermostatoOn = data.thermostat.switch;
        
        document.getElementById('t-current').innerText = currentTemp + " °C";
        document.getElementById('t-target').innerText = targetTemp + " °C";
        updateStatusUI('t-status', null, isTermostatoOn);
        
        // Alertas Dinámicas de Temperatura (PRD Especificación)
        const tempIcon = document.getElementById('t-icon');
        const tempValue = document.getElementById('t-current');
        
        // Limpiar clases de alertas previas
        tempIcon.className = "card-icon";
        tempValue.className = "data-value";
        
        if (currentTemp > 30) {
            // Temp > 30°C: Naranja
            tempIcon.classList.add('alert-temp-hot');
            tempValue.classList.add('alert-temp-hot');
        } else if (currentTemp < 10) {
            // Temp < 10°C: Azul
            tempIcon.classList.add('alert-temp-cold');
            tempValue.classList.add('alert-temp-cold');
        }
        
        // --- 2. Sincronización de Consumo General ---
        const powerW = data.pow.w;
        const voltageV = data.pow.v;
        
        document.getElementById('pow').innerText = powerW + " W";
        document.getElementById('vol').innerText = voltageV + " V";
        
        // Alerta de Potencia > 4000W: Borde rojo en la tarjeta
        const powerCard = document.getElementById('card-power');
        if (powerW > 4000) {
            powerCard.classList.add('alert-power-high');
        } else {
            powerCard.classList.remove('alert-power-high');
        }
        
        // --- 3. Sincronización de Agua Piscina (Relay 1) ---
        const isAguaOn = data.piscina.agua;
        updateStatusUI('ap-status-txt', 'ap-switch', isAguaOn);
        
        // --- 4. Sincronización de Reloj Piscina (Relay 2) ---
        const isRelojOn = data.piscina.reloj;
        updateStatusUI('rp-status-txt', 'rp-switch', isRelojOn);

        // --- 5. Sincronización de Aire cris ---
        if (data.aire) {
            const isAireOn = data.aire.power;
            const tempVal = data.aire.temp;
            const modeVal = data.aire.mode;
            const windVal = data.aire.wind;
            
            updateStatusUI('ac-status-txt', 'ac-switch', isAireOn);
            document.getElementById('ac-temp-val').innerText = tempVal;
            document.getElementById('ac-mode').value = modeVal;
            document.getElementById('ac-wind').value = windVal;
            
            // Activar o sombrear los controles según el estado de encendido
            setAcControlsState(isAireOn);
        }
        
    } catch (error) {
        console.error("Error al actualizar la telemetría del panel:", error);
    }
}

// Acción de encender/apagar el aire acondicionado
async function toggleAcPower(deviceId) {
    const switchEl = document.getElementById('ac-switch');
    const newState = switchEl.checked;
    
    // Actualizar UI inmediatamente (sensación de reactividad)
    updateStatusUI('ac-status-txt', 'ac-switch', newState);
    setAcControlsState(newState);
    
    try {
        const response = await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: deviceId, code: 'power', value: newState })
        });
        const res = await response.json();
        if (res.status !== 'success') {
            alert("Error al conmutar alimentación del aire");
            // Revertir UI si la nube rechaza el comando
            updateStatusUI('ac-status-txt', 'ac-switch', !newState);
            setAcControlsState(!newState);
        }
    } catch (e) {
        alert("Error de comunicación");
        updateStatusUI('ac-status-txt', 'ac-switch', !newState);
        setAcControlsState(!newState);
    }
}

// Enviar comandos genéricos de tipo select (modo, velocidad) al aire
async function sendAcCommand(deviceId, code, value) {
    try {
        const response = await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: deviceId, code: code, value: value })
        });
        const res = await response.json();
        if (res.status !== 'success') {
            alert(`Error al cambiar el parámetro ${code}`);
        }
    } catch (e) {
        alert("Error de comunicación");
    }
}

// Ajustar temperatura del aire por pasos (+1/-1)
async function adjustAcTemp(deviceId, step) {
    const tempValEl = document.getElementById('ac-temp-val');
    let currentTemp = parseInt(tempValEl.innerText);
    let newTemp = currentTemp + step;
    
    // Rango de temperatura según especificación (16°C a 30°C)
    if (newTemp < 16 || newTemp > 30) {
        return; // No hacer nada si se excede el rango
    }
    
    tempValEl.innerText = newTemp;
    
    try {
        const response = await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: deviceId, code: 'temp', value: newTemp })
        });
        const res = await response.json();
        if (res.status !== 'success') {
            alert("Error al ajustar temperatura");
            tempValEl.innerText = currentTemp; // Revertir en caso de fallo
        }
    } catch (e) {
        alert("Error de comunicación");
        tempValEl.innerText = currentTemp;
    }
}

// Activar botones personalizados del Aire (Mando DIY)
async function triggerAireCustom(keyIndex) {
    try {
        const response = await fetch('/api/trigger_aire_custom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: keyIndex })
        });
        const res = await response.json();
        if (res.status === 'success') {
            alert("Comando enviado con éxito.");
        } else {
            alert("Hubo un error al enviar el comando: " + (res.message || res.msg || "Desconocido"));
        }
    } catch (e) {
        alert("Error de comunicación con el servidor local");
    }
}

// Iniciar consulta de telemetría y programar intervalo cada 5 segundos
updateTelemetry();
setInterval(updateTelemetry, 5000);