from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group
from simple_history.models import HistoricalRecords
from ledgers.models import Household

class Board(models.Model):
    """
    관리자가 생성하고 그룹/사용자별 권한을 부여할 수 있는 게시판 모델
    """
    name = models.CharField(max_length=100, help_text="게시판 이름")
    description = models.TextField(blank=True, help_text="게시판 설명")
    
    # 참석 권한 설정 (빈 경우 누구나 접근 가능하도록 하거나, 로직에 따라 다르게 처리)
    allowed_groups = models.ManyToManyField(Group, blank=True, related_name='allowed_boards', help_text="접근을 허용할 그룹들")
    allowed_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='allowed_boards_direct', help_text="직접 접근을 허용할 개별 사용자들")

    # 익명 설정 및 게시판 관리자
    is_anonymous = models.BooleanField(default=False, verbose_name="익명 게시판 여부")
    board_admins = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='administered_boards', blank=True, verbose_name="게시판 관리자", help_text="이 게시판의 익명 작성자를 볼 수 있고 다른 사람의 글을 삭제/수정할 수 있습니다.")
    
    # 뷰 스타일 설정 (웹진형 vs 테이블형)
    LIST_STYLE_CHOICES = (
        ('table', '게시판형 (테이블)'),
        ('webzine', '웹진형 (썸네일)'),
    )
    list_style = models.CharField(max_length=20, choices=LIST_STYLE_CHOICES, default='table', verbose_name="목록 스타일", help_text="게시판 목록을 보여줄 형태를 선택하세요.")

    created_at = models.DateTimeField(auto_now_add=True)
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = '게시판 (Board)'
        verbose_name_plural = '게시판 목록 (Boards)'

    def __str__(self):
        return self.name

class Post(models.Model):
    """
    게시글 모델
    """
    title = models.CharField(max_length=200, help_text="게시글 제목")
    content = models.TextField(help_text="본문 내용")
    # 작성자: CustomUser와 연결되며, 사용자가 삭제되면 게시글도 삭제됩니다.
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    
    # 어떤 커뮤니티 게시판에 속하는가? (메모장인 경우 null일 수 있음)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='posts', null=True, blank=True)
    
    # 커뮤니티 게시글이면 null, 특정 가계부 전용 메모라면 가계부 정보를 가짐
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='memos', null=True, blank=True)
    
    # 사진 업로드 지원 (선택) - (다중 첨부로 인해 필드 삭제, PostMedia 모델에서 관리)
    # image = models.ImageField(upload_to='boards/%Y/%m/', blank=True, null=True, help_text="첨부 사진")
    
    views = models.PositiveIntegerField(default=0, verbose_name="조회수")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = '게시글 (Post)'
        verbose_name_plural = '게시글 목록 (Posts)'

    def __str__(self):
        if self.board:
            return f"[{self.board.name}] {self.title}"
        return f"[메모] {self.title}"

    @property
    def likes_count(self):
        return self.reactions.filter(reaction_type='like').count()

    @property
    def dislikes_count(self):
        return self.reactions.filter(reaction_type='dislike').count()

class Comment(models.Model):
    """
    게시글 댓글 모델
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(help_text="댓글 내용")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '댓글 (Comment)'
        verbose_name_plural = '댓글 목록 (Comments)'

    def __str__(self):
        return f"Comment by {self.author} on {self.post.title}"

    @property
    def likes_count(self):
        return self.reactions.filter(reaction_type='like').count()

    @property
    def dislikes_count(self):
        return self.reactions.filter(reaction_type='dislike').count()

class Reaction(models.Model):
    """
    게시글에 대한 좋아요/싫어요 반응을 저장하는 모델
    유저당 1개의 게시글에는 1번의 반응만 허용합니다.
    """
    REACTION_CHOICES = (
        ('like', '좋아요'),
        ('dislike', '싫어요'),
    )
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '게시글 반응 (Post Reaction)'
        verbose_name_plural = '게시글 반응 목록 (Post Reactions)'
        # 이 모델의 핵심: (post, user) 쌍이 중복되지 않도록 제한하여 1인칭 1반응 강제
        unique_together = ('post', 'user')

    def __str__(self):
        return f"{self.user} - {self.get_reaction_type_display()} on {self.post.title}"


class CommentReaction(models.Model):
    """
    댓글에 대한 좋아요/싫어요 반응을 저장하는 모델
    유저당 1개의 댓글에는 1번의 반응만 허용합니다.
    """
    REACTION_CHOICES = (
        ('like', '좋아요'),
        ('dislike', '싫어요'),
    )
    
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comment_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '댓글 반응 (Comment Reaction)'
        verbose_name_plural = '댓글 반응 목록 (Comment Reactions)'
        unique_together = ('comment', 'user')

    def __str__(self):
        return f"{self.user} - {self.get_reaction_type_display()} on Comment {self.comment.id}"

class PostMedia(models.Model):
    """
    게시글에 다중으로 첨부되는 미디어(사진/동영상) 모델
    """
    MEDIA_TYPE_CHOICES = (
        ('image', '사진'),
        ('video', '동영상'),
    )
    post = models.ForeignKey(Post, related_name='media_files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='boards/media/%Y/%m/', help_text="첨부 파일")
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '게시글 첨부 미디어 (Post Media)'
        verbose_name_plural = '게시글 첨부 미디어 목록 (Post Media)'

    def __str__(self):
        return f"{self.post.id}번 게시글의 {self.media_type}"
