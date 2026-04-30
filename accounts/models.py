from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from simple_history.models import HistoricalRecords

class CustomUserManager(BaseUserManager):
    """
    이메일을 고유 식별자(ID)로 사용하는 커스텀 유저 매니저
    기본 username 필드 대신 email 필드를 사용하여 유저를 생성합니다.
    """
    def create_user(self, email, password=None, **extra_fields):
        # 이메일 주소가 없으면 에러 발생
        if not email:
            raise ValueError('Email address is required')
        
        # 이메일 주소 정규화 (대소문자 처리 등)
        email = self.normalize_email(email)
        # 유저 인스턴스 생성
        user = self.model(email=email, **extra_fields)
        # 비밀번호 해싱 후 설정
        user.set_password(password)
        # DB에 저장
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        관리자(superuser) 계정 생성
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    """
    AbstractUser를 상속받은 커스텀 유저 모델
    로그인 시 이메일을 ID로 사용하도록 설정합니다.
    """
    # 기존 username 필드 제거
    username = None
    # 이메일 필드를 고유(unique) 필드로 설정
    email = models.EmailField('email address', unique=True)
    
    # 로그인 시 식별자로 이메일 사용 지정
    USERNAME_FIELD = 'email'
    # createsuperuser 명령 시 추가로 받을 필드를 지정 (여기서는 없음)
    REQUIRED_FIELDS = []

    # 사용자 추가 정보 (프로필 확장)
    profile_image = models.ImageField('프로필 사진', upload_to='profiles/%Y/%m/', blank=True, null=True)
    address = models.CharField('집 주소', max_length=255, blank=True)
    bio = models.TextField('자기소개', max_length=500, blank=True)

    # 사용자가 마지막으로 활성화했던 가계부 ID를 기억하는 보조 필드
    last_active_household_id = models.IntegerField(null=True, blank=True)

    history = HistoricalRecords()

    objects = CustomUserManager()

    class Meta:
        verbose_name = '사용자 (User)'
        verbose_name_plural = '사용자 목록 (Users)'

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        """
        사용자의 이름(first_name)이 있으면 이름을, 없으면 이메일 앞부분을 반환합니다.
        """
        if self.first_name:
            return self.first_name
        return self.email.split('@')[0]
