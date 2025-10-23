# Generated manually for Django 5.2+ compatibility
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