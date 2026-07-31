#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for virtual environment
if [ ! -f "venv/bin/activate" ]; then
    echo "Virtual environment not found. Run ./install.sh first."
    exit 1
fi

PYTHON="./venv/bin/python"

# Kill existing session if running
tmux kill-session -t chore_app 2>/dev/null

if ! command -v tmux &>/dev/null; then
    echo "Tmux is not installed. Running in the foreground..."
    exec $PYTHON manage.py runserver 0.0.0.0:8190
else
    tmux new-session -d -s chore_app "$PYTHON manage.py runserver 0.0.0.0:8190"
    if [ $? -eq 0 ]; then
        echo "Running chore_app in Tmux session 'chore_app'. Run 'tmux attach -t chore_app' to view logs."
    else
        echo "There was an error starting chore_app in Tmux."
        exit 1
    fi
fi
