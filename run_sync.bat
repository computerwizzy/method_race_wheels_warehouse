@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python sync.py >> sync.log 2>&1
