"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# (로컬 서버 기본) config.settings 대신 config.settings.local을 바라보도록 변경합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

application = get_asgi_application()
