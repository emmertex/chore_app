@echo off
set LOCK_FILE=INSTALL_LOCK

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python 3 is not installed. Installing...
    if exist "%ProgramFiles%\Python39\python.exe" (
    ) else (
        echo Installing Python 3...
        choco install python -y
    )
)

where django-admin >nul 2>nul
if %errorlevel% neq 0 (
    echo Django is not installed. Installing...
    python -m pip install django django-allauth 
)

python manage.py makemigrations
python manage.py makemigrations chore_app
python manage.py migrate

if exist "%LOCK_FILE%" (
    echo Skipping import of settings due to LOCK_FILE
) else (
    python manage.py loaddata settings.json
    echo . > "%LOCK_FILE%"
)