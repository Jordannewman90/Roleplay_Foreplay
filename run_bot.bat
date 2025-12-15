@echo off
echo Starting Roleplay & Foreplay Bot Setup...

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo Starting Bot...
python main.py

pause
