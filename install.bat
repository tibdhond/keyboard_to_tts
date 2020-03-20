@echo off
cmd /k "pip install virtualenv & virtualenv venv & cd /d .\venv\Scripts & activate & cd /d ..\.. & pip install --upgrade pip & pip install -r requirements.txt & exit"