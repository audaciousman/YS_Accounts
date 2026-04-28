from django.contrib import admin
from .models import Post, Comment, Reaction

# 댓글 관리를 더 직관적으로 하기 위한 Inline 모델
class CommentInline(admin.TabularInline):
    """
    Post 관리자 화면 내에서 해당 게시글의 댓글을 바로 보고 관리할 수 있게 해줍니다.
    """
    model = Comment
    extra = 1

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'likes', 'dislikes', 'created_at')
    # 카테고리별(자유, 꿀팁, 질문), 작성자별 필터 기능 활성화
    list_filter = ('category', 'author')
    search_fields = ('title', 'content')
    inlines = [CommentInline]  # 게시글 수정 창에서 댓글(Comment)도 함께 관리

    # 커스텀 메서드로 좋아요/싫어요 개수 표시
    def likes(self, obj):
        return obj.likes_count
    likes.short_description = '좋아요'

    def dislikes(self, obj):
        return obj.dislikes_count
    dislikes.short_description = '싫어요'

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    # 댓글 관리를 별도의 탭에서도 수행 가능한 전용 어드민 뷰
    list_display = ('post', 'author', 'content_snippet', 'created_at')
    list_filter = ('author', 'post')
    search_fields = ('content',)

    def content_snippet(self, obj):
        return obj.content[:30] + '...' if len(obj.content) > 30 else obj.content
    content_snippet.short_description = '내용'

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'reaction_type', 'created_at')
    list_filter = ('reaction_type',)
