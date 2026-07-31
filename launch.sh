#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for virtual environment
if [ ! -f "venv/bin/activate" ]; then
    echo "Virtual environment not found. Run ./install.sh first."
    exit 1
fi

PYTHON="./venv/bin/python"

if ! command -v screen &>/dev/null; then
    echo "Screen is not installed. Running in the foreground..."
    exec $PYTHON manage.py runserver 0.0.0.0:8190
else
    screen -d -m -S "chore_app" $PYTHON manage.py runserver 0.0.0.0:8190
    if [ $? -eq 0 ]; then
        echo "Running chore_app in Screen. Run 'screen -r chore_app' to attach."
    else
        echo "There was an error starting chore_app in Screen."
        exit 1
    fi
fi
