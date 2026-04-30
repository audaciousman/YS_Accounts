from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from simple_history.admin import SimpleHistoryAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm

class CustomUserAdmin(SimpleHistoryAdmin, UserAdmin):
    """
    관리자 페이지에 커스텀 유저를 노출하고 관리할 수 있도록 설정
    """
    # 이메일을 ID로 사용하도록 폼 교체
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'impersonate_link')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    def impersonate_link(self, obj):
        url = reverse('accounts:impersonate', args=[obj.pk])
        return format_html('<a class="button" href="{}">대리 로그인</a>', url)
    impersonate_link.short_description = '계정 접속'
    
    # 관리자 페이지 상세 필드셋에서 username 제거 및 email 배치
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('인적 사항 (Personal info)', {'fields': ('first_name', 'last_name', 'profile_image', 'address', 'bio')}),
        ('권한 (Permissions)', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('중요 날짜 (Important dates)', {'fields': ('last_login', 'date_joined')}),
    )
    
    # 신규 유저 추가 시 노출할 필드셋 (Password hashing & confirmation을 위한 password1, password2 사용)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'is_staff', 'is_active'),
        }),
    )

# 관리자 페이지에 CustomUser 모델 등록
admin.site.register(CustomUser, CustomUserAdmin)
