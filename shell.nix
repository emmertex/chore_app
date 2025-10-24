{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    tmux
    python313
    python313Packages.pip
    python313Packages.virtualenv
    python313Packages.setuptools
    python313Packages.wheel
  ];
  
  shellHook = ''
    # Lock file to avoid re-importing initial data on every shell enter
    LOCK_FILE="INSTALL_LOCK"
    echo "Setting up Python virtual environment..."
    if [ ! -d "venv" ]; then
        python -m venv venv
    fi
    source venv/bin/activate
    echo "Virtual environment activated. Installing Python packages..."
    pip install --upgrade pip
    pip install django django-allauth django-cron
    echo "Python packages installed."
    
    # Patch django-cron model for Django 5.x if upstream still ships index_together
    python - <<'PY'
import pathlib
p = pathlib.Path('venv/lib/python3.13/site-packages/django_cron/models.py')
if p.exists():
    txt = p.read_text()
    if 'index_together' in txt:
        lines = txt.splitlines()
        out, skip, depth = [], False, 0
        for line in lines:
            if not skip and 'index_together' in line:
                skip = True
                # track nested brackets () and [] until we close the block
                depth = line.count('[') + line.count('(') - (line.count(']') + line.count(')'))
                continue
            if skip:
                depth += line.count('[') + line.count('(') - (line.count(']') + line.count(')'))
                if depth <= 0:
                    skip = False
                continue
            out.append(line)
        p.write_text('\n'.join(out))
        print('Patched django_cron/models.py to remove index_together')
PY

    # Fix django-cron migrations for Django 5.2+ compatibility
    echo "Fixing django-cron migrations for Django 5.2+ compatibility..."
    python fix_django_cron_migrations.py
    
    # Run Django migrations if needed
    echo "Running Django migrations..."
    python manage.py makemigrations chore_app || true
    # Ensure custom user/tables exist before other app data migrations that reference it
    python manage.py migrate chore_app
    python manage.py migrate
    python manage.py check
    
    # Load initial data if lock file doesn't exist
    if [ ! -f "$LOCK_FILE" ]; then
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
