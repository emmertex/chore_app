#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Detected OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'"' -f2 || echo 'unknown')"

# Ensure Python 3 and pip are installed
if ! command -v python3 &>/dev/null; then
    echo "Python 3 is not installed. Installing..."
    if command -v apt &>/dev/null; then
        sudo apt update && sudo apt install -y python3 python3-pip python3-venv
    elif command -v pacman &>/dev/null; then
        sudo pacman -Syu --noconfirm python python-pip
    elif command -v yum &>/dev/null || command -v dnf &>/dev/null; then
        PKGMGR=$(command -v dnf 2>/dev/null || echo yum)
        sudo $PKGMGR install -y python3 python3-pip
    else
        echo "Unable to auto-install Python 3. Please install it manually."
        exit 1
    fi
fi

# Ensure pip is available
if ! python3 -m pip --version &>/dev/null; then
    echo "pip not found. Installing..."
    if command -v apt &>/dev/null; then
        sudo apt install -y python3-pip python3-venv
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python-pip
    else
        curl -sS https://bootstrap.pypa.io/get-pip.py | python3
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ]; then
    echo "Creating virtual environment..."
    rm -rf venv
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
echo "Installing Python dependencies..."
pip install --upgrade pip
# Pin Django <5.1 for django-cron compatibility (django-cron 0.6.0 uses index_together, removed in 5.1+)
pip install "django<5.1" django-allauth django-cron

echo "Running migrations..."
python manage.py makemigrations
python manage.py makemigrations chore_app || true
python manage.py migrate

LOCK_FILE="INSTALL_LOCK"
if [ ! -f "$LOCK_FILE" ]; then
    echo "Loading initial settings data..."
    python manage.py loaddata settings.json
    touch "$LOCK_FILE"
else
    echo "Settings already loaded (INSTALL_LOCK exists)."
fi

echo "Installation complete! Run ./launch.sh to start the server."
deactivate
