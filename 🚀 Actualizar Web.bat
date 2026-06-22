@echo off
chcp 65001 > nul
cd /d "%~dp0"
python agente_deploy.py
pause
