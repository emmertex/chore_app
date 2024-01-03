@echo off
python3 manage.py runserver 0.0.0.0:8000
if errorlevel 1 (
    echo Server failed to start.
) else (
    echo Server is running.
)