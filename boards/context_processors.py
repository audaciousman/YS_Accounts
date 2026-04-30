from django.db.models import Q
from .models import Board

def user_boards(request):
    """
    현재 로그인한 사용자가 접근 가능한 게시판 목록을 반환합니다.
    (base.html 사이드바 등에 전역적으로 사용됨)
    """
    if request.user.is_authenticated:
        boards = Board.objects.filter(
            Q(allowed_users=request.user) | 
            Q(allowed_groups__in=request.user.groups.all()) |
            Q(allowed_groups__isnull=True, allowed_users__isnull=True)
        ).distinct()
        return {'available_boards': boards}
    return {'available_boards': []}
