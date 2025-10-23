#!/usr/bin/env bash
# NixOS development script for chore_app
# Combines installation and launch, keeps you in nix-shell for development

LOCK_FILE="INSTALL_LOCK"

# Check if shell.nix exists, if not create it
if [ ! -f "shell.nix" ]; then
    echo "Creating shell.nix file..."
    cat > shell.nix << 'EOF'
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python313
    python313Packages.pip
    python313Packages.virtualenv
    python313Packages.setuptools
    python313Packages.wheel
  ];
  
  shellHook = ''
    echo "Setting up Python virtual environment..."
    if [ ! -d "venv" ]; then
        python -m venv venv
    fi
    source venv/bin/activate
    echo "Virtual environment activated. Installing Python packages..."
    pip install --upgrade pip
    pip install django django-allauth django-cron
    echo "Python packages installed."
    
    # Fix django-cron migrations for Django 5.2+ compatibility
    echo "Fixing django-cron migrations for Django 5.2+ compatibility..."
    python fix_django_cron_migrations.py
    
    # Run Django migrations if needed
    echo "Running Django migrations..."
    python manage.py makemigrations
    python manage.py makemigrations chore_app
    python manage.py migrate
    
    # Load initial data if lock file doesn't exist
    lock_file_exists=false
    if [ -f "$LOCK_FILE" ]; then
        lock_file_exists=true
    fi
    
    if ! $lock_file_exists; then
        echo "Loading initial data..."
        python manage.py loaddata settings.json
        touch "$LOCK_FILE"
        echo "Initial data loaded."
    else
        echo "Initial data already loaded (lock file exists)."
    fi
    
    echo ""
    echo "=========================================="
    echo "Development environment ready!"
    echo "=========================================="
    echo "Available commands:"
    echo "  python manage.py runserver 0.0.0.0:8000  # Start development server"
    echo "  python manage.py shell                   # Django shell"
    echo "  python manage.py migrate                 # Run migrations"
    echo "  python manage.py makemigrations          # Create migrations"
    echo "  deactivate                               # Exit virtual environment"
    echo "  exit                                     # Exit nix-shell"
    echo "=========================================="
    echo ""
  '';
}
EOF
fi

echo "Entering nix-shell development environment..."
echo "This will set up the environment and keep you in the shell for development."
echo ""

# Enter nix-shell and keep the user inside
nix-shell
