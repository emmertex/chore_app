if ! command -v screen &> /dev/null; then
    echo "Screen is is not installed. Running in the foreground..."
    python3 manage.py runserver 0.0.0.0:8000
else
    screen -d -m -S "chore_app" python3 manage.py runserver 0.0.0.0:8000
    if [ $? -eq 0 ]; then
        echo "Running chore_app in Screen. Run screen -r chore_app to attach."
    else
        echo "There was an error starting chore_app in Screen."
    fi
fi