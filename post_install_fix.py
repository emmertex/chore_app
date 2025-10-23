#!/usr/bin/env python3
"""
Post-installation fix for django-cron migrations.
This script should be run after any package installation to ensure
django-cron migrations are compatible with Django 5.2+.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_django_cron_fix():
    """Run the django-cron fix script."""
    try:
        # Run the fix script
        result = subprocess.run([sys.executable, 'fix_django_cron_migrations.py'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print("✅ django-cron migrations fixed successfully!")
            return True
        else:
            print(f"❌ Error fixing django-cron migrations: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running django-cron fix: {e}")
        return False


def main():
    """Main function."""
    print("Running post-installation django-cron fix...")
    
    if not os.path.exists('fix_django_cron_migrations.py'):
        print("❌ fix_django_cron_migrations.py not found!")
        return False
    
    return run_django_cron_fix()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
