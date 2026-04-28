FROM python:3.12-slim

# 환경변수 설정: 파이썬 출력 버퍼링 끄기, .pyc 파일 생성 안하기
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 필수 시스템 패키지 설치 (PostgreSQL 관련 등)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 파이썬 패키지 설치
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 전체 코드 복사
COPY . /app/

# 포트 오픈
EXPOSE 8000

# Gunicorn으로 서버 실행
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
