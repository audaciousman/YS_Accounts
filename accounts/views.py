from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from .forms import SignUpForm, UserProfileUpdateForm
from .models import CustomUser

class SignUpView(CreateView):
    """
    회원가입 요청을 처리하는 뷰 
    가입 성공 시 로그인 페이지로 자동 이동합니다.
    """
    form_class = SignUpForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    가입된 유저의 정보를 수정하는 뷰 (이름 변경 전용)
    """
    model = CustomUser
    form_class = UserProfileUpdateForm
    template_name = 'registration/profile_edit.html'
    success_url = reverse_lazy('ledgers:dashboard')

    def get_object(self, queryset=None):
        # 주소창에 id를 받지 않아도 항상 '현재 로그인한 본인'의 정보를 가져옵니다.
        return self.request.user


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """
    비밀번호를 변경하는 뷰
    Django의 기본 PasswordChangeView를 사용하여 비밀번호 변경 후에도 
    자동으로 세션을 유지시키는 기능인 update_session_auth_hash를 내부적으로 실행합니다.
    """
    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('ledgers:dashboard')
