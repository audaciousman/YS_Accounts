# 스마트 가계부 및 커뮤니티 (Django + TailwindCSS)

## 🚀 로컬 서버 실행 가이드 (Getting Started)

1. **가상환경 활성화**
   ```bash
   # Windows (명령 프롬프트/PowerShell)
   venv\Scripts\activate
   ```

2. **의존성 패키지 설치**
   ```bash
   pip install -r requirements.txt
   ```

3. **데이터베이스 마이그레이션 적용**
   ```bash
   python manage.py makemigrations accounts ledgers boards
   python manage.py migrate
   ```

4. **관리자(Superuser) 계정 생성**
   ```bash
   python manage.py createsuperuser
   # 이메일 주소와 비밀번호를 입력합니다.
   ```

5. **로컬 서버 실행**
   ```bash
   python manage.py runserver
   ```

6. **접속**
   - 사용자 화면: [http://127.0.0.1:8000/ledgers/](http://127.0.0.1:8000/ledgers/)
   - 관리자 화면: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
