@echo off
cd /d "e:\mobile_app\backend"

:: If you have a virtual environment folder inside the backend (like "venv"), uncomment the next line to activate it:
:: call venv\Scripts\activate.bat

:loop
echo [%time%] Checking for unboarded students...
python manage.py notify_unboarded_students

echo Waiting for 60 seconds before the next check...
:: Wait for 60 seconds (/t 60) without requiring a keypress (/nobreak)
timeout /t 60 /nobreak >nul

goto loop
