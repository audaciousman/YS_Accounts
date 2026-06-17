# 스마트 가계부 및 커뮤니티 (YS_Accounts)

이 문서는 작업 환경이 바뀌거나 새로운 컴퓨터/IDE(예: Antigravity IDE)에서 프로젝트를 처음부터 구축할 때 필요한 모든 정보를 담고 있습니다.

---

## 🚀 1. 기본 환경 세팅 (로컬 개발 환경)

### 1-1. 가상환경 생성 및 활성화
```bash
# 가상환경 생성
python -m venv venv

# Windows (명령 프롬프트/PowerShell)
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 1-2. 의존성 패키지 설치
`requirements.txt`에 명시된 패키지를 설치합니다.
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 1-3. 환경 변수(.env) 설정
프로젝트 루트에 있는 `.env.sample` 파일을 복사하여 `.env` 파일을 생성하고 적절한 값으로 수정합니다.
```bash
cp .env.sample .env
# Windows의 경우: copy .env.sample .env
```
> **참고**: 로컬 개발 시에는 SQLite를 기본으로 사용하므로 `DATABASE_URL`을 비워두거나 세팅하지 않아도 됩니다. 배포 시에는 PostgreSQL 정보를 입력해야 합니다.

---

## 🏃‍♂️ 2. 로컬 서버 실행 가이드

### 2-1. 데이터베이스 마이그레이션
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2-2. 관리자(Superuser) 계정 생성
초기 접속을 위해 관리자 계정을 생성합니다.
```bash
python manage.py createsuperuser
# 사용자 이름(ID), 이메일, 비밀번호 입력
```

### 2-3. 개발 서버 실행
```bash
python manage.py runserver
```
- **사용자 화면**: [http://127.0.0.1:8000/ledgers/](http://127.0.0.1:8000/ledgers/)
- **관리자 화면**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🐳 3. Synology NAS / Docker 배포 가이드

운영 환경(NAS 등)에서는 Docker 및 `docker-compose`를 사용하여 PostgreSQL과 함께 실행합니다.

### 3-1. 환경 설정 및 파일 준비
운영 서버의 프로젝트 디렉토리 내에 `.env` 파일을 만들고 아래와 같이 설정합니다 (예시):
```ini
DJANGO_SECRET_KEY=your_production_secret_key_here
DEBUG=False
ALLOWED_HOSTS=*
# Docker compose의 postgres 컨테이너 설정과 일치해야 함
DATABASE_URL=postgres://ys_user:ys_super_secret_pw@db:5432/ys_accounts
```

### 3-2. Docker 컨테이너 실행
```bash
# 백그라운드에서 빌드 및 실행
docker-compose up -d --build
```
> `docker-compose.yml`에는 `collectstatic` 및 `migrate` 명령어가 자동 실행되도록 설정되어 있습니다.
> 웹 서버는 `8000` 포트로 바인딩되며 Gunicorn으로 실행됩니다.

### 3-3. 미디어 및 DB 볼륨 (데이터 보존)
- **DB 데이터**: `postgres_data` 도커 볼륨에 영구 저장됩니다.
- **미디어 파일**: 프로젝트 내 `./media` 폴더와 동기화됩니다.

---

## 💾 4. 기존 데이터 복원 (옵션)
프로젝트 내에 저장된 기존 백업 데이터(`datadump.json`)가 있다면, 초기 마이그레이션 직후에 아래 명령어로 데이터를 불러올 수 있습니다.
```bash
python manage.py loaddata datadump.json
```

---

## 🤖 5. Antigravity IDE 등 새로운 AI 환경으로 넘어갈 때

새로운 환경에서 AI 비서(Antigravity 등)와 대화를 시작할 때, 이전 문맥을 유지하기 위해 다음 프롬프트를 첫 메시지로 입력하세요.

> **"프로젝트 루트에 있는 `README.md` 파일과 `Antigravity_대화요약.md` 파일을 먼저 읽고 현재 스마트 가계부(YS_Accounts) 프로젝트의 환경과 이전 작업 문맥을 파악해 줘. 그 이후에 내가 요청하는 작업을 진행해 주면 돼."**

이렇게 하면 AI가 프로젝트의 기술 스택, 배포 환경(NAS Docker), 그리고 이전 대화의 진행 상태를 완벽히 숙지하고 작업을 이어나갈 수 있습니다.
