import json
from django.http import JsonResponse, HttpResponseRedirect
from django.views import View
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from ledgers.views import get_active_household
from .models import Post, Reaction, Comment, CommentReaction

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
        referer = request.META.get('HTTP_REFERER', reverse('boards:post_list'))
        from urllib.parse import urlparse, urlencode, urlunparse, parse_qsl
        
        parsed = urlparse(referer)
        query = dict(parse_qsl(parsed.query))
        query['open_comments'] = post_id
        parsed = parsed._replace(query=urlencode(query))
        
        # 해시 스크롤 이동 지정
        new_url = urlunparse(parsed) + f"#post-{post_id}"
        
        return HttpResponseRedirect(new_url)

class PostListView(ListView):
    """
    게시판의 글 목록을 보여주며 카테고리 필터링이 가능합니다.
    """
    model = Post
    template_name = 'boards/post_list.html'
    context_object_name = 'posts'
    
    def get_queryset(self):
        # 퍼블릭 게시물만 가져오기 (가계부에 종속되지 않은 글)
        qs = super().get_queryset().filter(household__isnull=True)
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category=category)
        
        # [쿼리셋 최적화] 작성자(author) 및 댓글/댓글 작성자에 대한 N+1 문제 완전 예방
        return qs.select_related('author').prefetch_related('comments', 'comments__author').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_category'] = self.request.GET.get('category', 'all')
        return context

class PostCreateView(LoginRequiredMixin, CreateView):
    """
    새로운 게시글을 작성하는 뷰
    """
    model = Post
    fields = ['title', 'category', 'content', 'image']
    template_name = 'boards/post_form.html'
    success_url = reverse_lazy('boards:post_list')

    def form_valid(self, form):
        # 작성자를 현재 로그인한 유저로 자동 설정합니다.
        form.instance.author = self.request.user
        form.instance.household = None
        return super().form_valid(form)

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    작성자 본인만 수정할 수 있도록 권한(UserPassesTestMixin)을 통제하는 수정 뷰
    """
    model = Post
    fields = ['title', 'category', 'content', 'image']
    template_name = 'boards/post_form.html'
    success_url = reverse_lazy('boards:post_list')

    # UserPassesTestMixin에서 체크하는 권한 검증 메서드입니다.
    def test_func(self):
        post = self.get_object()
        # 로그인 사용자와 게시글 소유자가 일치해야 True 반환 (접근 허용)
        return self.request.user == post.author

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    작성자 본인만 삭제할 수 있는 삭제 뷰
    """
    model = Post
    template_name = 'boards/post_confirm_delete.html'
    success_url = reverse_lazy('boards:post_list')

    # 수정과 동일하게 작성자 본인 확인
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author


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
        return Post.objects.filter(household=active_hh).select_related('author').prefetch_related('comments', 'comments__author').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_memo_board'] = True
        return context

class MemoCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['title', 'content', 'image']  # 카테고리 선택 제외
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
        return super().form_valid(form)

class MemoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['title', 'content', 'image']
    template_name = 'boards/post_form.html'
    success_url = reverse_lazy('boards:memo_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_memo'] = True
        return context

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
