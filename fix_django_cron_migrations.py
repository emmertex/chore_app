#!/usr/bin/env python3
"""
Fix django-cron migrations for Django 5.2+ compatibility.
This script removes old migrations with index_together and creates clean ones.

Run this script after installing dependencies on fresh installations.
"""

import os
import shutil
import sys
from pathlib import Path


def find_django_cron_migrations():
    """Find the django-cron migrations directory in the virtual environment."""
    # Look for django_cron in site-packages
    for path in sys.path:
        if 'site-packages' in path:
            migrations_path = os.path.join(path, 'django_cron', 'migrations')
            if os.path.exists(migrations_path):
                return migrations_path
    return None


def backup_old_migrations(migrations_path):
    """Backup old migrations before deletion."""
    backup_path = os.path.join(os.getcwd(), 'backup_django_cron_migrations')
    if os.path.exists(backup_path):
        shutil.rmtree(backup_path)
    shutil.copytree(migrations_path, backup_path)
    print(f"Backed up old migrations to: {backup_path}")


def clean_migrations(migrations_path):
    """Remove all old migration files except __init__.py."""
    for file in os.listdir(migrations_path):
        if file.startswith('000') and file.endswith('.py'):
            file_path = os.path.join(migrations_path, file)
            os.remove(file_path)
            print(f"Removed: {file}")
    
    # Remove __pycache__ if it exists
    pycache_path = os.path.join(migrations_path, '__pycache__')
    if os.path.exists(pycache_path):
        shutil.rmtree(pycache_path)
        print("Removed __pycache__ directory")


def create_clean_initial_migration(migrations_path):
    """Create a new clean initial migration."""
    migration_content = '''# Generated manually for Django 5.2+ compatibility
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CronJobLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=64, db_index=True)),
                ('start_time', models.DateTimeField(db_index=True)),
                ('end_time', models.DateTimeField(db_index=True)),
                ('is_success', models.BooleanField(default=False)),
                ('message', models.TextField(default='', blank=True)),
                ('ran_at_time', models.TimeField(null=True, blank=True, db_index=True, editable=False)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['code', 'is_success', 'ran_at_time'], name='django_cron_code_is_success_ran_at_time_idx'),
                    models.Index(fields=['code', 'start_time', 'ran_at_time'], name='django_cron_code_start_time_ran_at_time_idx'),
                    models.Index(fields=['code', 'start_time'], name='django_cron_code_start_time_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='CronJobLock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_name', models.CharField(max_length=200, unique=True)),
                ('locked', models.BooleanField(default=False)),
            ],
        ),
    ]
'''
    
    migration_file = os.path.join(migrations_path, '0001_initial.py')
    with open(migration_file, 'w') as f:
        f.write(migration_content)
    print(f"Created clean initial migration: {migration_file}")


def main():
    """Main function to fix django-cron migrations."""
    print("Fixing django-cron migrations for Django 5.2+ compatibility...")
    
    migrations_path = find_django_cron_migrations()
    if not migrations_path:
        print("Error: Could not find django_cron migrations directory")
        sys.exit(1)
    
    print(f"Found django_cron migrations at: {migrations_path}")
    
    # Backup old migrations
    backup_old_migrations(migrations_path)
    
    # Clean old migrations
    clean_migrations(migrations_path)
    
    # Create new clean migration
    create_clean_initial_migration(migrations_path)
    
    print("\n✅ django-cron migrations fixed successfully!")
    print("You can now run: python manage.py migrate")


if __name__ == '__main__':
    main()
