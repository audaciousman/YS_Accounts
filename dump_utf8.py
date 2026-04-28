import os
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

with open('datadump.json', 'w', encoding='utf-8') as f:
    call_command('dumpdata', natural_foreign=True, natural_primary=True, exclude=['contenttypes', 'auth.Permission', 'admin.logentry'], indent=4, stdout=f)
