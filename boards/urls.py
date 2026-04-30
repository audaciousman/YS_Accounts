from django.urls import path
from .views import (
    CommunityHomeView,
    PostReactionView, PostListView, PostDetailView, PostCreateView, PostUpdateView, PostDeleteView,
    MemoListView, MemoCreateView, MemoUpdateView, MemoDeleteView,
    CommentCreateView, CommentReactionView
)

app_name = 'boards'

urlpatterns = [
    # 커뮤니티 대문
    path('community/', CommunityHomeView.as_view(), name='home'),

    # 게시판 접근 (기본 게시판으로 리다이렉트되거나 첫 화면)
    path('', PostListView.as_view(), name='post_list_all'),
    path('board/<int:board_id>/', PostListView.as_view(), name='post_list'),
    path('board/<int:board_id>/create/', PostCreateView.as_view(), name='post_create'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post_detail'),
    path('post/<int:pk>/edit/', PostUpdateView.as_view(), name='post_edit'),
    path('post/<int:pk>/delete/', PostDeleteView.as_view(), name='post_delete'),
    
    # 비동기 (AJAX) 좋아요 싫어요 처리 엔드포인트
    path('<int:post_id>/react/', PostReactionView.as_view(), name='react'),
    path('comment/<int:comment_id>/react/', CommentReactionView.as_view(), name='comment_react'),
    
    # 댓글 작성
    path('<int:post_id>/comment/', CommentCreateView.as_view(), name='comment_create'),
    
    # 워크스페이스 전용 메모 라우트
    path('memos/', MemoListView.as_view(), name='memo_list'),
    path('memos/create/', MemoCreateView.as_view(), name='memo_create'),
    path('memos/<int:pk>/edit/', MemoUpdateView.as_view(), name='memo_edit'),
    path('memos/<int:pk>/delete/', MemoDeleteView.as_view(), name='memo_delete'),
]
