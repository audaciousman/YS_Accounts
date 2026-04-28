from django.urls import path
from .views import (
    PostReactionView, PostListView, PostCreateView, PostUpdateView, PostDeleteView,
    MemoListView, MemoCreateView, MemoUpdateView, MemoDeleteView,
    CommentCreateView, CommentReactionView
)

app_name = 'boards'

urlpatterns = [
    path('', PostListView.as_view(), name='post_list'),
    path('create/', PostCreateView.as_view(), name='post_create'),
    path('<int:pk>/edit/', PostUpdateView.as_view(), name='post_edit'),
    path('<int:pk>/delete/', PostDeleteView.as_view(), name='post_delete'),
    
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
