@echo off
chcp 65001 >nul
cd /d "%~dp0"
call conda activate torch313
python main.py

