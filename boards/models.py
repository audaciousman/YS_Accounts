from django.db import models
from django.conf import settings
from ledgers.models import Household

class Post(models.Model):
    """
    게시글 모델
    자유, 꿀팁, 질문 세 가지 카테고리를 지원합니다.
    """
    CATEGORY_CHOICES = (
        ('free', '자유'),
        ('tip', '꿀팁'),
        ('question', '질문'),
        ('memo', '개인 메모'),
    )
    
    title = models.CharField(max_length=200, help_text="게시글 제목")
    content = models.TextField(help_text="본문 내용")
    # 작성자: CustomUser와 연결되며, 사용자가 삭제되면 게시글도 삭제됩니다.
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='free')
    
    # 커뮤니티 게시글이면 null, 특정 가계부 전용 메모라면 가계부 정보를 가짐
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='memos', null=True, blank=True)
    
    # 사진 업로드 지원 (선택)
    image = models.ImageField(upload_to='boards/%Y/%m/', blank=True, null=True, help_text="첨부 사진")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

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
        unique_together = ('comment', 'user')

    def __str__(self):
        return f"{self.user} - {self.get_reaction_type_display()} on Comment {self.comment.id}"
