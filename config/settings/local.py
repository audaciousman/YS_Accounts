"""
Django 로컬 환경 설정 파일 (local.py)
개발 중 본인의 컴퓨터(로컬 환경)에서만 실행할 설정입니다. base.py의 설정을 상속받아 사용합니다.
"""

from .base import *

# 로컬 개발 환경이므로 디버그 모드를 켜서 에러 메시지를 상세히 확인합니다.
DEBUG = True

# 로컬 서버 주소 허용
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# 개발용 데이터베이스 설정 (SQLite3)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
