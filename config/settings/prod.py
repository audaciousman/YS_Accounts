"""
Django 운영 환경 설정 파일 (prod.py)
실제로 서비스가 배포되었을 때(운영 환경) 실행할 설정입니다. base.py의 설정을 상속받아 사용합니다.
"""

from .base import *

# 진짜 서비스를 제공하는 환경이므로 디버그 모드는 절대 꺼둡니다. (정보 유출 방지)
DEBUG = False

# 나중에 도메인을 적용하면 이곳에 도메인 주소를 넣습니다.
ALLOWED_HOSTS = ['*']

# 운영 환경용 데이터베이스 (예시로 sqlite3를 두었으나, 실무에서는 PostgreSQL 등으로 교체합니다)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
