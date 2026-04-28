from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def index_redirect(request):
    """
    루트(/) 페이지 접속 시:
    - 로그인되어 있다면가계부 메인(/ledgers/)으로 이동
    - 로그아웃 상태라면 로그인 화면으로 이동하되, 로그인 직후 /ledgers/ 로 오도록 next 처리
    """
    if request.user.is_authenticated:
        return redirect('ledgers:dashboard')
    else:
        return redirect('/accounts/login/?next=/ledgers/')

urlpatterns = [
    path('', index_redirect, name='index'),
    path('admin/', admin.site.urls),
    # 각 앱별 URL 라우팅 연결 
    path('boards/', include('boards.urls')),
    path('ledgers/', include('ledgers.urls')),
    # accounts의 커스텀 라우팅(회원가입 등)
    path('accounts/', include('accounts.urls')),
    # accounts의 기본 로그인/로그아웃 시스템을 활용하기 위해 include 추가 가능
    path('accounts/', include('django.contrib.auth.urls')),
]

# 개발 모드(DEBUG=True)일 때, 사용자가 업로드한 미디어 파일(사진, 영수증 등)을 서빙하기 위한 세팅
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
