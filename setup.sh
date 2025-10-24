#!/usr/bin/env bash
# Setup script for chore_app - run this after git pull or fresh clone

echo "Setting up chore_app environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade packages
echo "Installing/upgrading Python packages..."
pip install --upgrade pip
pip install django django-allauth django-cron

# Fix django-cron migrations for Django 5.2+ compatibility
echo "Fixing django-cron migrations for Django 5.2+ compatibility..."
python fix_django_cron_migrations.py

# Run migrations
echo "Running Django migrations..."
python manage.py makemigrations
python manage.py makemigrations chore_app
python manage.py migrate

# Load initial data if needed
LOCK_FILE="INSTALL_LOCK"
if [ ! -f "$LOCK_FILE" ]; then
    echo "Loading initial data..."
    python manage.py loaddata settings.json
    touch "$LOCK_FILE"
    echo "Initial data loaded."
else
    echo "Initial data already loaded (lock file exists)."
fi

echo ""
echo "✅ Setup complete! You can now run:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver"
echo ""
