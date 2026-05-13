import datetime
import calendar
import json
from django.db.models import Sum, Q, Count
from django.db.models.functions import TruncDate
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
import csv
from django.shortcuts import redirect, get_object_or_404, reverse, render
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.contrib import messages
from .models import Transaction, Household, Category, Asset
from .forms import TransactionForm


def get_active_household(request):
    """
    현재 접속한 사용자의 데이터에 기반해 활성 가계부를 결정합니다.
    1순위: 세션의 active_household_id
    2순위: DB의 user.last_active_household_id
    3순위: 그룹(group) 가계부 우선 탐색
    4순위: 소유한 첫 번째 가계부
    """
    if not request.user.is_authenticated:
        return None
        
    households = Household.objects.filter(
        Q(admin_user=request.user) | Q(members=request.user)
    ).distinct()
    
    if not households.exists():
        return None
        
    active_id = request.session.get('active_household_id')
    if not active_id:
        active_id = getattr(request.user, 'last_active_household_id', None)
        
    if active_id:
        active_hh = households.filter(id=active_id).first()
        if active_hh:
            request.session['active_household_id'] = active_hh.id
            return active_hh
            
    # 3순위: 세션도, 마지막 기록도 없다면 그룹 가계부를 우선 탐색
    active_hh = households.filter(household_type='group').order_by('id').first()
    if not active_hh:
        active_hh = households.order_by('id').first()
        
    # 결정된 가계부를 세션과 DB에 보존
    request.session['active_household_id'] = active_hh.id
    if hasattr(request.user, 'last_active_household_id'):
        request.user.last_active_household_id = active_hh.id
        request.user.save(update_fields=['last_active_household_id'])
        
    return active_hh


class HouseholdSwitchView(LoginRequiredMixin, View):
    """가계부(워크스페이스) 전환 기능을 수행하는 뷰"""
    def post(self, request, pk):
        households = Household.objects.filter(
            Q(admin_user=request.user) | Q(members=request.user)
        ).distinct()
        
        hh = get_object_or_404(households, pk=pk)
        
        # 세션과 DB에 모두 활성 가계부 상태 저장
        request.session['active_household_id'] = hh.id
        if hasattr(request.user, 'last_active_household_id'):
            request.user.last_active_household_id = hh.id
            request.user.save(update_fields=['last_active_household_id'])
        
        referer = request.META.get('HTTP_REFERER', reverse_lazy('ledgers:dashboard'))
        return HttpResponseRedirect(referer)


def _get_prev_month_day(year, month, day):
    """전월 동일 일자 반환. 말일 초과 시 해당 월 말일로 조정."""
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    max_day = calendar.monthrange(prev_year, prev_month)[1]
    return datetime.date(prev_year, prev_month, min(day, max_day))


def get_household_date_range(request_get, household):
    """GET 파라미터 → 급여일 기준 전체 주기 → 이번달 1일~말일 순으로 날짜 범위 결정."""
    from django.utils import timezone
    import datetime, calendar
    
    date_from_str = request_get.get('date_from')
    date_to_str = request_get.get('date_to')

    if date_from_str and date_to_str:
        try:
            return (datetime.date.fromisoformat(date_from_str),
                    datetime.date.fromisoformat(date_to_str))
        except ValueError:
            pass

    today = timezone.localdate()
    salary_day = None
    if household:
        salary_cat = Category.objects.filter(
            household=household, type='income', payment_day__isnull=False
        ).first()
        if salary_cat:
            salary_day = salary_cat.payment_day

    if salary_day:
        if today.day < salary_day:
            date_from = _get_prev_month_day(today.year, today.month, salary_day)
        else:
            max_day = calendar.monthrange(today.year, today.month)[1]
            date_from = today.replace(day=min(salary_day, max_day))
        
        # 다음 급여일 전날까지 (전체 한 주기)
        next_year, next_month = date_from.year, date_from.month + 1
        if next_month > 12:
            next_month = 1
            next_year += 1
        next_max_day = calendar.monthrange(next_year, next_month)[1]
        next_salary_date = datetime.date(next_year, next_month, min(salary_day, next_max_day))
        date_to = next_salary_date - datetime.timedelta(days=1)
    else:
        date_from = today.replace(day=1)
        max_day = calendar.monthrange(today.year, today.month)[1]
        date_to = today.replace(day=max_day)

    return date_from, date_to


class LedgerDashboardView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'ledgers/dashboard.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        household = get_active_household(self.request)
        if not household:
            return Transaction.objects.none()

        date_from, date_to = get_household_date_range(self.request.GET, household)
        return Transaction.objects.filter(
            household=household,
            date__gte=date_from,
            date__lte=date_to,
            is_deleted=False,           # 소프트 삭제 필터
        ).select_related('category', 'withdraw_asset', 'deposit_asset', 'user').order_by('-date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        household = get_active_household(self.request)
        date_from, date_to = get_household_date_range(self.request.GET, household)
        qs = self.get_queryset()

        # ── 기본 집계 ──────────────────────────────────────────────────────────
        income  = qs.filter(transaction_type='income').aggregate(t=Sum('amount'))['t'] or 0
        expense = qs.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or 0
        
        # 저축 연산: (저축 넣은 돈 합산 - 저축 다시 깬 돈 합산)
        savings_dep = qs.filter(transaction_type='savings_deposit').aggregate(t=Sum('amount'))['t'] or 0
        savings_wid = qs.filter(transaction_type='savings_withdraw').aggregate(t=Sum('amount'))['t'] or 0
        total_savings = savings_dep - savings_wid
        
        # 단순 이체(transfer)는 통계에 아무 영향을 주지 않습니다.
        
        context.update({
            'total_income':  income,
            'total_expense': expense,
            'total_savings': total_savings, # UI 호환성을 위해 변수명은 savings 유지
            'balance':       income - expense - total_savings,
            'date_from':     date_from,
            'date_to':       date_to,
        })

        # ── 급여일 버튼용 ──────────────────────────────────────────────────────
        today = timezone.localdate()
        salary_day = None
        if household:
            salary_cat = Category.objects.filter(
                household=household, type='income', payment_day__isnull=False
            ).first()
            if salary_cat:
                salary_day = salary_cat.payment_day
        context['salary_day'] = salary_day
        if salary_day:
            if today.day < salary_day:
                sal_from = _get_prev_month_day(today.year, today.month, salary_day)
            else:
                sal_from = today.replace(day=min(salary_day, calendar.monthrange(today.year, today.month)[1]))
            
            next_year, next_month = sal_from.year, sal_from.month + 1
            if next_month > 12:
                next_month = 1
                next_year += 1
            next_max_day = calendar.monthrange(next_year, next_month)[1]
            next_salary_date = datetime.date(next_year, next_month, min(salary_day, next_max_day))
            
            context['salary_date_from'] = sal_from
            context['salary_date_to']   = next_salary_date - datetime.timedelta(days=1)

        # ── 고정비 현황 (start_date~end_date 기간 내 활성 고정비) ──────────────
        if household:
            active_fixed_cats = Category.objects.filter(
                household=household,
                type='expense',
                is_fixed=True,
            ).filter(
                Q(start_date__isnull=True) | Q(start_date__lte=date_to)
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=date_from)
            )

            # 이미 거래 입력된 고정비 카테고리 ID 집합
            entered_ids = set(
                qs.filter(transaction_type='expense', category__is_fixed=True)
                .values_list('category_id', flat=True)
            )

            fixed_status = []
            for cat in active_fixed_cats:
                cat.is_entered = (cat.id in entered_ids)
                fixed_status.append(cat)

            context['fixed_status_list']    = fixed_status
            context['fixed_total_expected'] = sum(
                (cat.fixed_amount or 0) for cat in active_fixed_cats
            )
            context['fixed_entered_count']  = sum(1 for c in fixed_status if c.is_entered)
            context['fixed_pending_count']  = sum(1 for c in fixed_status if not c.is_entered)

        # ── 카테고리별 지출 요약 ───────────────────────────────────────────────
        cat_summary = (
            qs.filter(transaction_type='expense')
            .values('category__id', 'category__name', 'category__is_fixed')
            .annotate(total=Sum('amount'), cnt=Count('id'))
            .order_by('-total')
        )
        context['category_expense_summary'] = cat_summary
        context['uncategorized_expense'] = (
            qs.filter(transaction_type='expense', category__isnull=True)
            .aggregate(t=Sum('amount'))['t'] or 0
        )
        
        # 고정비 퀵적용 모달을 위한 자산 목록
        if household:
            context['active_assets'] = Asset.objects.filter(household=household, is_active=True)

        return context


# ── 통계 화면 View ─────────────────────────────────────────────────────────────
class LedgerStatsView(LoginRequiredMixin, ListView):
    """
    일자별 수입, 지출, 총저축 통계를 보여주고 시각화(Chart.js)를 위한 데이터를 제공하는 뷰입니다.
    대시보드와 동일하게 날짜 범위를 인식합니다.
    """
    model = Transaction
    template_name = 'ledgers/stats.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        household = get_active_household(self.request)
        if not household:
            return Transaction.objects.none()
        
        date_from, date_to = get_household_date_range(self.request.GET, household)
        return Transaction.objects.filter(
            household=household,
            is_deleted=False,
            date__gte=date_from,
            date__lte=date_to
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        
        household = get_active_household(self.request)
        date_from, date_to = get_household_date_range(self.request.GET, household)
            
        context['date_from'] = date_from
        context['date_to'] = date_to
        
        group_by = self.request.GET.get('group_by', 'day')
        context['group_by'] = group_by
        
        # 총 요약 데이터
        income  = qs.filter(transaction_type='income').aggregate(t=Sum('amount'))['t'] or 0
        expense = qs.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or 0
        savings_dep = qs.filter(transaction_type='savings_deposit').aggregate(t=Sum('amount'))['t'] or 0
        savings_wid = qs.filter(transaction_type='savings_withdraw').aggregate(t=Sum('amount'))['t'] or 0
        total_savings = savings_dep - savings_wid
        balance = income - expense - total_savings

        context.update({
            'total_income': income,
            'total_expense': expense,
            'total_savings': total_savings,
            'balance': balance,
        })

        # 일자별 데이터 처리 (이미 date가 DateField이므로 TruncDate 생략 가능)
        daily_stats = qs.values('date', 'transaction_type') \
                        .annotate(total=Sum('amount')) \
                        .order_by('date')
                        
        date_dict = {}
        for entry in daily_stats:
            if not entry['date']: continue
            dt = entry['date']
            
            if group_by == 'month':
                d_str = dt.strftime('%Y-%m')
            elif group_by == 'year':
                d_str = dt.strftime('%Y')
            else:
                d_str = dt.isoformat()
            
            if d_str not in date_dict:
                date_dict[d_str] = {
                    'income': 0, 'expense': 0, 'savings_deposit': 0, 'savings_withdraw': 0
                }
            ttype = entry['transaction_type']
            if ttype in date_dict[d_str]:
                date_dict[d_str][ttype] += float(entry['total'])
                
        labels = []
        income_data = []
        expense_data = []
        savings_data = []
        table_data = []
        
        if date_from and date_to:
            if group_by == 'month':
                curr = date_from.replace(day=1)
                end_m = date_to.replace(day=1)
                while curr <= end_m:
                    d_str = curr.strftime('%Y-%m')
                    labels.append(d_str)
                    inc = date_dict.get(d_str, {}).get('income', 0)
                    exp = date_dict.get(d_str, {}).get('expense', 0)
                    s_dep = date_dict.get(d_str, {}).get('savings_deposit', 0)
                    s_wid = date_dict.get(d_str, {}).get('savings_withdraw', 0)
                    net_sav = s_dep - s_wid
                    bal = inc - exp - net_sav
                    
                    income_data.append(inc)
                    expense_data.append(exp)
                    savings_data.append(net_sav)
                    table_data.append({
                        'date_label': d_str + '월',
                        'income': inc, 'expense': exp, 'savings': net_sav, 'balance': bal
                    })
                    
                    if curr.month == 12:
                        curr = curr.replace(year=curr.year+1, month=1)
                    else:
                        curr = curr.replace(month=curr.month+1)

            elif group_by == 'year':
                curr_y = date_from.year
                end_y = date_to.year
                while curr_y <= end_y:
                    d_str = str(curr_y)
                    labels.append(d_str)
                    inc = date_dict.get(d_str, {}).get('income', 0)
                    exp = date_dict.get(d_str, {}).get('expense', 0)
                    s_dep = date_dict.get(d_str, {}).get('savings_deposit', 0)
                    s_wid = date_dict.get(d_str, {}).get('savings_withdraw', 0)
                    net_sav = s_dep - s_wid
                    bal = inc - exp - net_sav
                    
                    income_data.append(inc)
                    expense_data.append(exp)
                    savings_data.append(net_sav)
                    table_data.append({
                        'date_label': d_str + '년',
                        'income': inc, 'expense': exp, 'savings': net_sav, 'balance': bal
                    })
                    curr_y += 1
            else:
                # day
                delta = date_to - date_from
                for i in range(delta.days + 1):
                    cur_date = date_from + datetime.timedelta(days=i)
                    d_str = cur_date.isoformat()
                    labels.append(d_str)
                    inc = date_dict.get(d_str, {}).get('income', 0)
                    exp = date_dict.get(d_str, {}).get('expense', 0)
                    s_dep = date_dict.get(d_str, {}).get('savings_deposit', 0)
                    s_wid = date_dict.get(d_str, {}).get('savings_withdraw', 0)
                    net_sav = s_dep - s_wid
                    bal = inc - exp - net_sav
                    
                    income_data.append(inc)
                    expense_data.append(exp)
                    savings_data.append(net_sav)
                    table_data.append({
                        'date_label': cur_date.strftime('%y.%m.%d'),
                        'income': inc, 'expense': exp, 'savings': net_sav, 'balance': bal
                    })
                
        table_data.reverse()
        
        context['chart_labels_json'] = json.dumps(labels)
        context['chart_income_json'] = json.dumps(income_data)
        context['chart_expense_json'] = json.dumps(expense_data)
        context['chart_savings_json'] = json.dumps(savings_data)
        context['table_data'] = table_data
        
        return context


# ── 거래 내역 소프트 삭제 ───────────────────────────────────────────────────────
class TransactionSoftDeleteView(LoginRequiredMixin, View):
    """DELETE 대신 is_deleted=True 로 처리하여 데이터 보존."""
    def post(self, request, pk):
        household = get_active_household(request)
        tx = get_object_or_404(Transaction, pk=pk, household=household, is_deleted=False)
        tx.is_deleted = True
        tx.save(update_fields=['is_deleted', 'updated_at'])
        # 이전 페이지(날짜 범위 포함)로 복귀
        referer = request.META.get('HTTP_REFERER', '/ledgers/')
        return HttpResponseRedirect(referer)


class GroupRequestCreateView(LoginRequiredMixin, CreateView):
    from .models import GroupRequest
    from .forms import GroupRequestForm
    model = GroupRequest
    form_class = GroupRequestForm
    template_name = 'ledgers/group_request_form.html'
    success_url = reverse_lazy('ledgers:dashboard')

    def form_valid(self, form):
        form.instance.requester = self.request.user
        return super().form_valid(form)

class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'ledgers/transaction_form.html'
    success_url = reverse_lazy('ledgers:dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['household'] = get_active_household(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_household'] = get_active_household(self.request)
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.household = get_active_household(self.request)
        return super().form_valid(form)

class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    """
    기존 가계부 내역을 수정하는 뷰
    """
    model = Transaction
    form_class = TransactionForm
    template_name = 'ledgers/transaction_form.html'
    
    def get_success_url(self):
        # 성공 시 대시보드로 돌아갑니다.
        return reverse_lazy('ledgers:dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['household'] = get_active_household(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_household'] = get_active_household(self.request)
        return context


# ── 가계부 설정 관리 ────────────────────────────────────────────────────────────

class LedgerSettingsView(LoginRequiredMixin, ListView):
    template_name = 'ledgers/settings.html'
    context_object_name = 'categories'

    def get_queryset(self):
        household = get_active_household(self.request)
        qs = Category.objects.filter(household=household)

        tab    = self.request.GET.get('tab', 'all')
        search = self.request.GET.get('search', '').strip()

        if tab == 'income':    qs = qs.filter(type='income')
        elif tab == 'expense': qs = qs.filter(type='expense')
        elif tab == 'savings': qs = qs.filter(type='savings')
        elif tab == 'fixed':   qs = qs.filter(is_fixed=True)
        elif tab == 'variable':qs = qs.filter(type__in=['expense', 'savings'], is_fixed=False)

        if search:
            qs = qs.filter(name__icontains=search)

        return qs.order_by('type', '-is_fixed', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        household = get_active_household(self.request)
        context['assets'] = Asset.objects.filter(household=household, is_active=True).order_by('asset_type', 'name')
        context['active_tab']       = self.request.GET.get('tab', 'all')
        context['search_query']     = self.request.GET.get('search', '')
        all_cats = Category.objects.filter(household=household)
        context['count_all']      = all_cats.count()
        context['count_income']   = all_cats.filter(type='income').count()
        context['count_expense']  = all_cats.filter(type='expense').count()
        context['count_savings']  = all_cats.filter(type='savings').count()
        context['count_fixed']    = all_cats.filter(is_fixed=True).count()
        context['count_variable'] = all_cats.filter(type__in=['expense', 'savings'], is_fixed=False).count()
        return context


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model    = Category
    fields   = ['name', 'type', 'is_fixed', 'payment_day', 'fixed_amount', 'start_date', 'end_date']
    template_name = 'ledgers/category_form.html'

    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('ledgers:settings')

    def form_valid(self, form):
        form.instance.household = get_active_household(self.request)
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model    = Category
    fields   = ['name', 'type', 'is_fixed', 'payment_day', 'fixed_amount', 'start_date', 'end_date']
    template_name = 'ledgers/category_form.html'

    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('ledgers:settings')

    def get_queryset(self):
        household = get_active_household(self.request)
        return Category.objects.filter(household=household)


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model       = Category
    success_url = reverse_lazy('ledgers:settings')

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def get_queryset(self):
        household = get_active_household(self.request)
        return Category.objects.filter(household=household)


class AssetCreateView(LoginRequiredMixin, CreateView):
    model    = Asset
    fields   = ['name', 'bank_name', 'account_number', 'asset_type', 'initial_balance', 'memo']
    template_name = 'ledgers/asset_form.html'

    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('ledgers:settings')

    def form_valid(self, form):
        form.instance.household = get_active_household(self.request)
        return super().form_valid(form)


class AssetUpdateView(LoginRequiredMixin, UpdateView):
    model    = Asset
    fields   = ['name', 'bank_name', 'account_number', 'asset_type', 'initial_balance', 'memo']
    template_name = 'ledgers/asset_form.html'

    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('ledgers:settings')

    def get_queryset(self):
        household = get_active_household(self.request)
        return Asset.objects.filter(household=household)


class AssetDeleteView(LoginRequiredMixin, DeleteView):
    model       = Asset
    success_url = reverse_lazy('ledgers:settings')

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def get_queryset(self):
        household = get_active_household(self.request)
        return Asset.objects.filter(household=household)


class FixedTransactionQuickAddView(LoginRequiredMixin, View):
    """
    고정비 항목을 대시보드에서 빠르게 적용(생성)하는 뷰
    """
    def post(self, request, *args, **kwargs):
        household = get_active_household(request)
        if not household:
            messages.error(request, '가계부를 찾을 수 없습니다.')
            return redirect('ledgers:dashboard')

        category_id = request.POST.get('category_id')
        date_str = request.POST.get('date')
        amount_str = request.POST.get('amount')
        description = request.POST.get('description')
        withdraw_asset_id = request.POST.get('withdraw_asset_id')

        try:
            category = Category.objects.get(id=category_id, household=household)
            withdraw_asset = Asset.objects.get(id=withdraw_asset_id, household=household)
            amount = int(amount_str)
            tx_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

            Transaction.objects.create(
                household=household,
                user=request.user,
                date=tx_date,
                transaction_type='expense',
                category=category,
                withdraw_asset=withdraw_asset,
                amount=amount,
                description=description
            )
            messages.success(request, f'[{category.name}] 고정비가 내역에 적용되었습니다.')
        except Exception as e:
            messages.error(request, f'고정비 적용 중 오류가 발생했습니다: {str(e)}')

        # 돌아갈 곳이 있으면 돌아가기
        referer = request.META.get('HTTP_REFERER', reverse('ledgers:dashboard'))
        return HttpResponseRedirect(referer)


def download_batch_template(request):
    """
    일괄 추가용 CSV 템플릿 파일 다운로드 제공
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transaction_batch_template.csv"'
    # 한글 깨짐 방지를 위한 BOM 추가
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    writer.writerow([
        '날짜(YYYY-MM-DD)', 
        '유형(수입/지출/이체/저축 넣기/저축 빼기)', 
        '분류명', 
        '출금자산명', 
        '입금자산명', 
        '금액', 
        '사용처(선택)',
        '내역(적요)'
    ])
    # 예시 데이터 제공
    writer.writerow(['2026-04-10', '지출', '식비', '메인 카드', '', '15000', '스타벅스', '점심 식사'])
    writer.writerow(['2026-04-10', '수입', '급여', '', '급여통장', '3000000', '', '4월 급여'])
    writer.writerow(['2026-04-11', '이체', '', '급여통장', '메인 카드', '500000', '', '카드대금 이체'])
    
    return response


class TransactionBatchCreateView(LoginRequiredMixin, View):
    """
    가계부 내역 일괄 추가 화면 및 JSON 처리 API
    """
    def get(self, request, *args, **kwargs):
        household = get_active_household(request)
        if not household:
            messages.error(request, '활성화된 가계부가 없습니다.')
            return redirect('ledgers:dashboard')
            
        categories = list(Category.objects.filter(household=household).values('id', 'name', 'type'))
        assets = list(Asset.objects.filter(household=household, is_active=True).values('id', 'name'))
        
        context = {
            'active_household': household,
            'categories_json': json.dumps(categories),
            'assets_json': json.dumps(assets),
        }
        return render(request, 'ledgers/transaction_batch_form.html', context)
        
    def post(self, request, *args, **kwargs):
        household = get_active_household(request)
        if not household:
            return JsonResponse({'success': False, 'message': '활성화된 가계부가 없습니다.'})
            
        try:
            data = json.loads(request.body)
            transactions_data = data.get('transactions', [])
            
            created_count = 0
            for row in transactions_data:
                # 데이터 추출
                date_str = row.get('date')
                tx_type = row.get('type')
                category_id = row.get('category_id')
                withdraw_id = row.get('withdraw_asset_id')
                deposit_id = row.get('deposit_asset_id')
                amount = int(row.get('amount', 0))
                merchant = row.get('merchant', '')
                description = row.get('description', '')
                
                # 빈 행 스킵
                if not date_str or not tx_type or not amount or not description:
                    continue
                    
                tx_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # 객체 조회
                category = Category.objects.filter(id=category_id, household=household).first() if category_id else None
                withdraw = Asset.objects.filter(id=withdraw_id, household=household).first() if withdraw_id else None
                deposit = Asset.objects.filter(id=deposit_id, household=household).first() if deposit_id else None
                
                Transaction.objects.create(
                    household=household,
                    user=request.user,
                    date=tx_date,
                    transaction_type=tx_type,
                    category=category,
                    withdraw_asset=withdraw,
                    deposit_asset=deposit,
                    amount=amount,
                    merchant=merchant,
                    description=description
                )
                created_count += 1
                
            messages.success(request, f'성공적으로 {created_count}건의 내역을 일괄 등록했습니다.')
            return JsonResponse({'success': True, 'redirect_url': reverse('ledgers:dashboard')})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'오류가 발생했습니다: {str(e)}'})

def download_asset_batch_template(request):
    """
    자산 일괄 추가용 CSV 템플릿 다운로드
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="asset_batch_template.csv"'
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    writer.writerow([
        '자산명(예: 농협통장)', 
        '은행/카드사(예: 농협)', 
        '계좌/카드번호', 
        '자산유형(현금/입출금 통장/저축/신용카드/포인트/투자/대출/보험)', 
        '초기잔액(숫자만)', 
        '메모'
    ])
    writer.writerow(['생활비 통장', '신한은행', '110-123-456789', '입출금 통장', '500000', '생활비 전용'])
    writer.writerow(['메인 카드', '현대카드', '1234-5678-XXXX-XXXX', '신용카드', '0', ''])
    
    return response

class AssetBatchCreateView(LoginRequiredMixin, View):
    """
    자산 일괄 추가 화면 및 JSON 처리 API
    """
    def get(self, request, *args, **kwargs):
        household = get_active_household(request)
        if not household:
            messages.error(request, '활성화된 가계부가 없습니다.')
            return redirect('ledgers:dashboard')
            
        context = {
            'active_household': household,
        }
        return render(request, 'ledgers/asset_batch_form.html', context)
        
    def post(self, request, *args, **kwargs):
        household = get_active_household(request)
        if not household:
            return JsonResponse({'success': False, 'message': '활성화된 가계부가 없습니다.'})
            
        try:
            data = json.loads(request.body)
            assets_data = data.get('assets', [])
            
            created_count = 0
            for row in assets_data:
                name = row.get('name')
                bank_name = row.get('bank_name', '')
                account_number = row.get('account_number', '')
                asset_type = row.get('asset_type', 'bank')
                initial_balance = int(row.get('initial_balance', 0) or 0)
                memo = row.get('memo', '')
                
                if not name:
                    continue
                
                Asset.objects.create(
                    household=household,
                    name=name,
                    bank_name=bank_name,
                    account_number=account_number,
                    asset_type=asset_type,
                    initial_balance=initial_balance,
                    memo=memo
                )
                created_count += 1
                
            messages.success(request, f'성공적으로 {created_count}건의 자산을 일괄 등록했습니다.')
            return JsonResponse({'success': True, 'redirect_url': reverse('ledgers:settings')})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'오류가 발생했습니다: {str(e)}'})

def download_category_batch_template(request):
    """
    분류 일괄 추가용 CSV 템플릿 다운로드
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="category_batch_template.csv"'
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    writer.writerow([
        '유형(수입/지출)', 
        '분류명(예: 식비)', 
        '고정비여부(O/X)'
    ])
    writer.writerow(['지출', '식비', 'X'])
    writer.writerow(['지출', '통신비', 'O'])
    writer.writerow(['수입', '월급', 'O'])
    
    return response

class CategoryBatchCreateView(LoginRequiredMixin, View):
    """
    분류 일괄 추가 화면 및 JSON 처리 API
    """
    def get(self, request, *args, **kwargs):
        household = get_active_household(request)
        if not household:
            messages.error(request, '활성화된 가계부가 없습니다.')
            return redirect('ledgers:dashboard')
            
        context = {
            'active_household': household,
        }
        return render(request, 'ledgers/category_batch_form.html', context)
        
    def post(self, request, *args, **kwargs):
        household = get_active_household(request)
        if not household:
            return JsonResponse({'success': False, 'message': '활성화된 가계부가 없습니다.'})
            
        try:
            data = json.loads(request.body)
            categories_data = data.get('categories', [])
            
            created_count = 0
            for row in categories_data:
                type_val = row.get('type')
                name = row.get('name')
                is_fixed_raw = row.get('is_fixed', 'X')
                is_fixed = True if str(is_fixed_raw).strip().upper() == 'O' else False
                
                if not name or type_val not in ['income', 'expense']:
                    continue
                
                Category.objects.create(
                    household=household,
                    type=type_val,
                    name=name,
                    is_fixed=is_fixed
                )
                created_count += 1
                
            messages.success(request, f'성공적으로 {created_count}건의 분류를 일괄 등록했습니다.')
            return JsonResponse({'success': True, 'redirect_url': reverse('ledgers:settings')})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'오류가 발생했습니다: {str(e)}'})

