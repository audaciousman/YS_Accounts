from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
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

    def form_valid(self, form):
        # 회원가입 성공 메시지 (로그인 페이지 등에서 출력됨)
        messages.success(self.request, "회원가입이 완료되었습니다. 관리자 승인 후 로그인할 수 있습니다.")
        return super().form_valid(form)

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


class ImpersonateUserView(UserPassesTestMixin, View):
    """
    최고관리자가 다른 유저로 대리 로그인하는 뷰
    """
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, pk, *args, **kwargs):
        target_user = get_object_or_404(CustomUser, pk=pk)
        
        # 현재 최고 관리자 ID를 세션에 저장
        impersonator_id = request.user.id
        
        # 대상 유저로 로그인
        login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')
        
        # 세션에 복귀용 ID 기록
        request.session['impersonator_id'] = impersonator_id
        
        messages.success(request, f'{target_user.email} 계정으로 대리 로그인 되었습니다.')
        return redirect('ledgers:dashboard')


class UnimpersonateUserView(LoginRequiredMixin, View):
    """
    대리 로그인을 종료하고 원래 최고관리자 계정으로 복귀하는 뷰
    """
    def get(self, request, *args, **kwargs):
        impersonator_id = request.session.get('impersonator_id')
        if not impersonator_id:
            messages.error(request, '대리 로그인 상태가 아닙니다.')
            return redirect('ledgers:dashboard')
            
        impersonator = get_object_or_404(CustomUser, pk=impersonator_id)
        
        # 관리자 계정으로 다시 로그인
        login(request, impersonator, backend='django.contrib.auth.backends.ModelBackend')
        
        # 세션에서 대리 로그인 정보 삭제
        if 'impersonator_id' in request.session:
            del request.session['impersonator_id']
            
        messages.success(request, '원래 관리자 계정으로 복귀했습니다.')
        return redirect('admin:accounts_customuser_changelist')
