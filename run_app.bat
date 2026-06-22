@echo off
:: Inicia el servidor local minimizado y abre el navegador
start /min python servidor.py --mode local
rem timeout /t 3
start http://127.0.0.1:5050
exit