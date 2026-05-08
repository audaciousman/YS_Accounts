from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    """
    유저 생성 시 사용하는 폼 (가입 등)
    기본 username 필드 대신 email 사용
    """
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # 관리자 페이지 유저 추가 화면(add)에서 입력받을 필드들을 지정합니다.
        fields = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')

class CustomUserChangeForm(UserChangeForm):
    """
    유저 정보 수정 시 사용하는 폼
    """
    class Meta:
        model = CustomUser
        fields = ('email',)

class SignUpForm(UserCreationForm):
    """
    일반 사용자용 회원가입 폼
    관리자 권한 필드를 배제하고 사용자 정보만 받습니다.
    """
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'last_name', 'first_name')
        
    def save(self, commit=True):
        user = super().save(commit=False)
        # 회원가입 시 기본으로 비활성화 (관리자 승인 대기)
        user.is_active = False 
        if commit:
            user.save()
        return user

from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

class CustomAuthenticationForm(AuthenticationForm):
    """
    비활성 계정에 대해 구체적인 에러 메시지를 제공하기 위한 커스텀 로그인 폼
    """
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                "관리자 승인 대기 중이거나 비활성화된 계정입니다. 승인 후 다시 시도해주세요.",
                code='inactive',
            )
        super().confirm_login_allowed(user)

class UserProfileUpdateForm(forms.ModelForm):
    """
    마이페이지(개인정보 수정)에서 사용하는 폼
    이메일은 아이디이므로 수정 불가하게 하거나 원할 시 수정 가능하게 할 수 있으나
    보안상 이름만 변경할 수 있도록 합니다.
    """
    class Meta:
        model = CustomUser
        fields = ('last_name', 'first_name', 'profile_image', 'address', 'bio')
