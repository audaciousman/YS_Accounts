"""
Django 운영 환경 설정 파일 (prod.py)
실제로 서비스가 배포되었을 때(운영 환경) 실행할 설정입니다. base.py의 설정을 상속받아 사용합니다.
"""

from .base import *
import environ

env = environ.Env()

# 도커 환경에서 환경변수를 로드합니다
DEBUG = False

# 나중에 도메인을 적용하면 이곳에 도메인 주소(또는 NAS IP)를 넣습니다.
ALLOWED_HOSTS = ['*']

# 운영 환경용 데이터베이스 (PostgreSQL)
# 도커 compose에서 DATABASE_URL을 주입해주면 자동으로 파싱하여 연결합니다.
# 기본값으로 sqlite3를 두어 로컬에서 바로 실행할 때 에러가 나지 않게 합니다.
DATABASES = {
    'default': env.db('DATABASE_URL', default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}
