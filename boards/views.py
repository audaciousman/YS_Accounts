import json
from django.http import JsonResponse, HttpResponseRedirect
from django.views import View
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q, F, Count
from django.core.exceptions import PermissionDenied
from ledgers.views import get_active_household
from .models import Board, Post, Reaction, Comment, CommentReaction

class CommunityHomeView(LoginRequiredMixin, View):
    """
    모든 커뮤니티 게시판의 최신글/인기글을 모아서 보여주는 포털 대문 뷰
    """
    def get(self, request, *args, **kwargs):
        # 1. 사용자가 볼 수 있는 게시판들
        boards = Board.objects.filter(
            Q(allowed_users=request.user) | Q(allowed_groups__in=request.user.groups.all()) | Q(allowed_groups__isnull=True, allowed_users__isnull=True)
        ).distinct()
        
        # 2. 글로벌 인기글 (조회수 기준 상위 5개)
        hot_posts = Post.objects.filter(board__in=boards).select_related('board', 'author').prefetch_related('comments').order_by('-views', '-created_at')[:5]
        
        # 3. 각 게시판별 최신글 5개씩 묶기
        board_latest_posts = []
        for b in boards:
            latest = Post.objects.filter(board=b).select_related('author').prefetch_related('comments').order_by('-created_at')[:5]
            if latest.exists():
                board_latest_posts.append({
                    'board': b,
                    'posts': latest
                })
                
        context = {
            'hot_posts': hot_posts,
            'board_latest_posts': board_latest_posts,
        }
        return render(request, 'boards/community_home.html', context)


class PostReactionView(LoginRequiredMixin, View):
    """
    AJAX(Fetch API) 요청을 처리하여 좋아요/싫어요 숫자를 갱신하는 뷰.
    새로고침 없이 요청이 처리되어야 하므로 JSON 응답을 반환합니다.
    """
    def post(self, request, *args, **kwargs):
        post_id = kwargs.get('post_id')
        post_obj = get_object_or_404(Post, id=post_id)
        
        try:
            data = json.loads(request.body)
            action = data.get('action') 
        except json.JSONDecodeError:
            return JsonResponse({'error': '잘못된 데이터 형식입니다.'}, status=400)
            
        if action not in ['like', 'dislike']:
            return JsonResponse({'error': '허용되지 않는 반응입니다.'}, status=400)

        reaction, created = Reaction.objects.get_or_create(
            post=post_obj,
            user=request.user,
            defaults={'reaction_type': action}
        )

        if not created:
            if reaction.reaction_type == action:
                reaction.delete()
                status_msg = f"{action} 취소됨"
            else:
                reaction.reaction_type = action
                reaction.save()
                status_msg = f"{action}으로 변경됨"
        else:
            status_msg = f"{action} 추가됨"

        # 최종 반응 개수를 전달하여 프론트에서 실시간으로 DOM을 갱신합니다.
        return JsonResponse({
            'status': status_msg,
            'likes_count': post_obj.likes_count,
            'dislikes_count': post_obj.dislikes_count
        })

class CommentReactionView(LoginRequiredMixin, View):
    """
    댓글의 좋아요/싫어요 AJAX 요청을 처리하는 뷰 
    """
    def post(self, request, *args, **kwargs):
        comment_id = kwargs.get('comment_id')
        comment_obj = get_object_or_404(Comment, id=comment_id)
        
        try:
            data = json.loads(request.body)
            action = data.get('action') 
        except json.JSONDecodeError:
            return JsonResponse({'error': '잘못된 데이터 형식입니다.'}, status=400)
            
        if action not in ['like', 'dislike']:
            return JsonResponse({'error': '허용되지 않는 반응입니다.'}, status=400)

        reaction, created = CommentReaction.objects.get_or_create(
            comment=comment_obj,
            user=request.user,
            defaults={'reaction_type': action}
        )

        if not created:
            if reaction.reaction_type == action:
                reaction.delete()
                status_msg = f"{action} 취소됨"
            else:
                reaction.reaction_type = action
                reaction.save()
                status_msg = f"{action}으로 변경됨"
        else:
            status_msg = f"{action} 추가됨"

        return JsonResponse({
            'status': status_msg,
            'likes_count': comment_obj.likes_count,
            'dislikes_count': comment_obj.dislikes_count
        })

class CommentCreateView(LoginRequiredMixin, View):
    """
    인라인 댓글 작성 뷰
    """
    def post(self, request, post_id):
        post_obj = get_object_or_404(Post, id=post_id)
        content = request.POST.get('content', '').strip()
        
        if content:
            Comment.objects.create(
                post=post_obj,
                author=request.user,
                content=content
            )
            
        # 기존 체류하던 리스트 페이지로 복귀하되, 방금 작성한 댓글창이 열려있도록 파라미터 추가
        referer = request.META.get('HTTP_REFERER')
        if not referer:
            referer = reverse('boards:post_list', kwargs={'board_id': post_obj.board_id})
        from urllib.parse import urlparse, urlencode, urlunparse, parse_qsl
        
        parsed = urlparse(referer)
        query = dict(parse_qsl(parsed.query))
        query['open_comments'] = post_id
        parsed = parsed._replace(query=urlencode(query))
        
        # 해시 스크롤 이동 지정
        new_url = urlunparse(parsed) + f"#post-{post_id}"
        
        return HttpResponseRedirect(new_url)

class PostListView(LoginRequiredMixin, ListView):
    """
    특정 게시판(Board)의 글 목록을 보여주며, 권한을 체크합니다.
    """
    model = Post
    template_name = 'boards/post_list.html'
    context_object_name = 'posts'
    
    def dispatch(self, request, *args, **kwargs):
        board_id = self.kwargs.get('board_id')
        if not board_id:
            # 기본 게시판 찾기 (내가 권한 있는 첫 번째 게시판)
            first_board = Board.objects.filter(
                Q(allowed_users=request.user) | Q(allowed_groups__in=request.user.groups.all()) | Q(allowed_groups__isnull=True, allowed_users__isnull=True)
            ).distinct().first()
            if first_board:
                return redirect('boards:post_list', board_id=first_board.id)
            else:
                self.board = None
                return super().dispatch(request, *args, **kwargs)
        
        self.board = get_object_or_404(Board, id=board_id)
        
        # 권한 체크
        if self.board.allowed_users.exists() or self.board.allowed_groups.exists():
            has_access = self.board.allowed_users.filter(id=request.user.id).exists() or \
                         self.board.allowed_groups.filter(id__in=request.user.groups.all()).exists()
            if not has_access and not request.user.is_superuser:
                raise PermissionDenied("이 게시판에 접근할 권한이 없습니다.")
                
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if not self.board:
            return Post.objects.none()
        qs = super().get_queryset().filter(board=self.board)
        # [쿼리셋 최적화] 작성자(author), 댓글 및 미디어 파일에 대한 N+1 문제 완전 예방
        return qs.select_related('author').prefetch_related('comments', 'comments__author', 'media_files').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_board'] = self.board
        
        is_board_admin = False
        if self.board and self.request.user.is_authenticated:
            if self.request.user.is_superuser or self.request.user.is_staff:
                is_board_admin = True
            elif self.board.board_admins.filter(id=self.request.user.id).exists():
                is_board_admin = True
        
        context['is_board_admin'] = is_board_admin
        
        # 인기글 추가 (조회수 기준)
        if self.board:
            context['popular_posts'] = self.get_queryset().order_by('-views')[:3]
            
        return context

class PostDetailView(LoginRequiredMixin, DetailView):
    """
    게시글 상세 화면을 보여주며, 권한을 체크하고 조회수를 증가시킵니다.
    """
    model = Post
    template_name = 'boards/post_detail.html'
    context_object_name = 'post'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # 조회수 증가 로직 (세션을 활용해 중복 조회 방지)
        viewed_session_key = f'viewed_post_{self.object.id}'
        if not request.session.get(viewed_session_key, False):
            self.object.views += 1
            self.object.save(update_fields=['views'])
            request.session[viewed_session_key] = True
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.board = self.object.board
        context['current_board'] = self.board
        
        is_board_admin = False
        if self.board and self.request.user.is_authenticated:
            if self.request.user.is_superuser or self.request.user.is_staff:
                is_board_admin = True
            elif self.board.board_admins.filter(id=self.request.user.id).exists():
                is_board_admin = True
        
        context['is_board_admin'] = is_board_admin
        return context

class PostCreateView(LoginRequiredMixin, CreateView):
    """
    특정 게시판에 새로운 게시글을 작성하는 뷰
    """
    model = Post
    fields = ['title', 'content']
    template_name = 'boards/post_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.board = get_object_or_404(Board, id=self.kwargs.get('board_id'))
        if self.board.allowed_users.exists() or self.board.allowed_groups.exists():
            has_access = self.board.allowed_users.filter(id=request.user.id).exists() or \
                         self.board.allowed_groups.filter(id__in=request.user.groups.all()).exists()
            if not has_access and not request.user.is_superuser:
                raise PermissionDenied("이 게시판에 글을 쓸 권한이 없습니다.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('boards:post_list', kwargs={'board_id': self.board.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_board'] = self.board
        return context

    def form_valid(self, form):
        # 작성자를 현재 로그인한 유저로 자동 설정합니다.
        form.instance.author = self.request.user
        form.instance.board = self.board
        form.instance.household = None
        response = super().form_valid(form)
        
        # 업로드된 다중 파일 처리
        files = self.request.FILES.getlist('media_files')
        for f in files:
            # 파일 확장자를 기반으로 미디어 타입 판단
            ext = f.name.split('.')[-1].lower()
            media_type = 'video' if ext in ['mp4', 'mov', 'avi', 'wmv', 'webm'] else 'image'
            from .models import PostMedia
            PostMedia.objects.create(post=self.object, file=f, media_type=media_type)
            
        return response

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    작성자 본인만 수정할 수 있도록 권한을 통제하는 수정 뷰
    """
    model = Post
    fields = ['title', 'content']
    template_name = 'boards/post_form.html'

    def get_success_url(self):
        return reverse('boards:post_list', kwargs={'board_id': self.object.board.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_board'] = self.object.board
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # 삭제할 미디어 처리
        delete_media_ids = self.request.POST.getlist('delete_media')
        if delete_media_ids:
            from .models import PostMedia
            PostMedia.objects.filter(id__in=delete_media_ids, post=self.object).delete()
            
        # 새로 업로드된 다중 파일 처리
        files = self.request.FILES.getlist('media_files')
        for f in files:
            ext = f.name.split('.')[-1].lower()
            media_type = 'video' if ext in ['mp4', 'mov', 'avi', 'wmv', 'webm'] else 'image'
            from .models import PostMedia
            PostMedia.objects.create(post=self.object, file=f, media_type=media_type)
        return response

    # UserPassesTestMixin에서 체크하는 권한 검증 메서드입니다.
    def test_func(self):
        post = self.get_object()
        # 작성자 본인이거나, 최고 관리자, 스태프, 또는 이 게시판의 관리자인 경우 허용
        if self.request.user == post.author:
            return True
        if self.request.user.is_superuser or self.request.user.is_staff:
            return True
        if post.board and post.board.board_admins.filter(id=self.request.user.id).exists():
            return True
        return False

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    작성자 본인 및 게시판 관리자가 삭제할 수 있는 삭제 뷰
    """
    model = Post
    template_name = 'boards/post_confirm_delete.html'

    def get_success_url(self):
        return reverse('boards:post_list', kwargs={'board_id': self.object.board.id})

    # 수정과 동일한 권한 확인
    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        if self.request.user.is_superuser or self.request.user.is_staff:
            return True
        if post.board and post.board.board_admins.filter(id=self.request.user.id).exists():
            return True
        return False


# ── 개인/워크스페이스 전용 메모 기능 ──────────────────────────────────────────

class MemoListView(LoginRequiredMixin, ListView):
    """
    현재 활성화된 워크스페이스(가계부) 멤버들만 볼 수 있는 프라이빗 메모 리스트
    """
    model = Post
    template_name = 'boards/memo_list.html'
    context_object_name = 'posts'
    
    def get_queryset(self):
        active_hh = get_active_household(self.request)
        if not active_hh:
            return Post.objects.none()
        return Post.objects.filter(household=active_hh).select_related('author').prefetch_related('comments', 'comments__author', 'media_files').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_memo_board'] = True
        return context

class MemoCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['title', 'content']  # 카테고리 선택 제외
    template_name = 'boards/post_form.html'
    success_url = reverse_lazy('boards:memo_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_memo'] = True
        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.category = 'memo'
        form.instance.household = get_active_household(self.request)
        response = super().form_valid(form)
        
        files = self.request.FILES.getlist('media_files')
        for f in files:
            ext = f.name.split('.')[-1].lower()
            media_type = 'video' if ext in ['mp4', 'mov', 'avi', 'wmv', 'webm'] else 'image'
            from .models import PostMedia
            PostMedia.objects.create(post=self.object, file=f, media_type=media_type)
            
        return response

class MemoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['title', 'content']
    template_name = 'boards/post_form.html'
    success_url = reverse_lazy('boards:memo_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_memo'] = True
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        files = self.request.FILES.getlist('media_files')
        for f in files:
            ext = f.name.split('.')[-1].lower()
            media_type = 'video' if ext in ['mp4', 'mov', 'avi', 'wmv', 'webm'] else 'image'
            from .models import PostMedia
            PostMedia.objects.create(post=self.object, file=f, media_type=media_type)
        return response

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author and post.household is not None

class MemoDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'boards/post_confirm_delete.html'
    success_url = reverse_lazy('boards:memo_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_memo'] = True
        return context

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author and post.household is not None
