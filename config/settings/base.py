"""
Django 기본 설정 파일 (base.py)
모든 환경(로컬, 운영)에서 공통으로 사용되는 설정을 정의합니다.
"""
from pathlib import Path
import os

# 프로젝트 최상단 디렉토리 경로 (BASE_DIR) 설정
# 기존 config/settings.py에서 config/settings/base.py로 위치가 변경되었으므로
# 부모 디렉토리(.parent)를 한 번 더 호출해 주어야 합니다.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 보안 경고: 환경 변수로 분리하여 관리해야 하는 중요한 비밀 키입니다. 
SECRET_KEY = 'django-insecure-ge3y##42m50lz_h+x(4=@&o(p4v*4=c4-1ub2)j^m_3y&kvlwe'

# 생성한 커스텀 앱들을 등록합니다. (계정, 가계부, 자유게시판)
LOCAL_APPS = [
    'accounts',
    'ledgers',
    'boards',
]

# Django 기본 내장 앱
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize', # 천 단위 콤마(intcomma) 등 다국어 숫자 포맷팅 지원
]

# 써드파티 앱들도 여기에 추가할 수 있습니다.
THIRD_PARTY_APPS = [
    'simple_history',
]

# INSTALL_APPS 통합
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# 미들웨어 설정
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

# 최상위 URL 설정 파일 지정
ROOT_URLCONF = 'config.urls'

# 템플릿 엔진 및 설정 지정
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 전체 프로젝트 공통 템플릿 폴더 경로 설정 (BASE_DIR / 'templates')
        'DIRS': [BASE_DIR / 'templates'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'ledgers.context_processors.household_context',
                'boards.context_processors.user_boards',
            ],
        },
    },
]

# WSGI 애플리케이션 진입점
WSGI_APPLICATION = 'config.wsgi.application'

# 패스워드 검증기
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# 다국어 처리 및 시간대 설정
LANGUAGE_CODE = 'ko-kr'   # 한국어로 변경 (관리자 페이지 등에서 한국어 사용)
TIME_ZONE = 'Asia/Seoul'  # 한국 시간대로 변경 (가계부 거래 시간 기록에 중요)
USE_I18N = True
USE_TZ = True

# 정적 파일 (CSS, JS, 폰트 등) 경로 설정
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# 미디어 파일 (사용자가 업로드한 영수증 이미지 등) 설정
# 웹 브라우저가 미디어 파일에 접근할 때 사용할 URL 경로
MEDIA_URL = '/media/'
# 실제 데이터베이스/서버 상에 파일이 저장되는 물리적 절대 경로
MEDIA_ROOT = BASE_DIR / 'media'

# 기본 자동 증가 PK (Primary Key) 필드 타입 설정
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# [1단계 용] 커스텀 유저 모델 지정
# accounts 앱 안에 선언할 CustomUser 모델을 프로젝트의 기본 유저 모델로 사용한다고 선언합니다.
AUTH_USER_MODEL = 'accounts.CustomUser'

LOGIN_REDIRECT_URL = '/ledgers/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
