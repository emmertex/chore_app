LOCK_FILE="INSTALL_LOCK"

if ! command -v python3 &>/dev/null; then
    echo "Python 3 is not installed. Installing..."
    if command -v apt &>/dev/null; then
        sudo apt install python3 python-pip
    elif command -v yum &>/dev/null; then
        sudo yum install python3 python-pip
    elif command -v emerge &>/dev/null; then
        sudo emerge -av dev-lang/python:3
    elif command -v pacman &>/dev/null; then
        sudo pacman -S python python-pip
    elif command -v brew &>/dev/null; then
        brew install python3
        easy_install pip
    else
        echo "Unable to install Python 3. Please install it manually."
    fi
fi

if ! command -v django-admin &>/dev/null; then
    echo "Django is not installed. Installing..."
    python3 -m pip install django django-allauth
fi

python3 manage.py makemigrations
python3 manage.py makemigrations chore_app
python3 manage.py migrate

lock_file_exists=false
if [ -f "$LOCK_FILE" ]; then
    lock_file_exists=true
fi

if ! $lock_file_exists; then
    python3 manage.py loaddata settings.json
    touch "$LOCK_FILE"
fi
