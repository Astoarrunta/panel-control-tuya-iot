@echo off
chcp 65001 > nul
echo.
echo ================================================
echo   DEPLOY: Panel Control Tuya Smart IoT V2.0
echo ================================================
echo.

REM Recibe el mensaje de commit como primer argumento
set COMMIT_MSG=%~1
if "%COMMIT_MSG%"=="" set COMMIT_MSG=update: cambios automaticos

echo [1/3] Añadiendo cambios al staging...
git add .
if errorlevel 1 goto error

echo [2/3] Creando commit: "%COMMIT_MSG%"
git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo      Sin cambios nuevos para commitear.
    goto fin
)

echo [3/3] Enviando a GitHub...
git push origin main
if errorlevel 1 goto error

echo.
echo ================================================
echo   OK: Codigo subido a GitHub correctamente!
echo ================================================
goto fin

:error
echo.
echo [ERROR] El proceso fallo. Revisa los mensajes anteriores.
exit /b 1

:fin
echo.
