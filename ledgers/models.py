from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from simple_history.models import HistoricalRecords

class Household(models.Model):
    """
    가계부 그룹을 나타내는 모델.
    """
    HOUSEHOLD_TYPE_CHOICES = (
        ('personal', '개인'),
        ('group', '그룹'),
    )
    
    name = models.CharField(max_length=100)
    household_type = models.CharField(max_length=20, choices=HOUSEHOLD_TYPE_CHOICES, default='personal')
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='managed_households')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='households', blank=True)
    
    budget_start_day = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name="가계부 주기 시작일",
        help_text="매월 이 날짜를 가계부 주기의 시작일로 설정합니다. (예: 1이면 1일~말일, 25이면 25일~24일)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = '가계부 (Household)'
        verbose_name_plural = '가계부 목록 (Households)'

    def __str__(self):
        return f"{self.name} ({self.get_household_type_display()})"


class GroupRequest(models.Model):
    """
    일반 사용자가 그룹 가계부 생성을 관리자에게 요청하는 모델
    """
    STATUS_CHOICES = (
        ('pending', '대기 중'),
        ('approved', '승인됨'),
        ('rejected', '거절됨'),
    )
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_requests', verbose_name="요청자")
    requested_members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='group_invites', blank=True, verbose_name="포함할 멤버", help_text="이 그룹에 포함할 멤버들을 선택하세요.")
    name = models.CharField(max_length=100, unique=True, verbose_name="그룹 이름", help_text="중복되지 않는 고유한 그룹 이름을 입력하세요.")
    description = models.TextField(verbose_name="설명(Memo)", help_text="이 그룹의 목적이나 설명을 자유롭게 작성해주세요.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="상태")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="요청 일시")

    class Meta:
        verbose_name = '그룹 생성 요청 (Group Request)'
        verbose_name_plural = '그룹 생성 요청 목록 (Group Requests)'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.name} - by {self.requester}"


class Category(models.Model):
    """
    수입과 지출의 상세 분류(카테고리). 사용자가 직접 생성 및 관리.
    """
    CATEGORY_TYPE_CHOICES = (
        ('income', '수입'),
        ('expense', '지출'),
        ('savings', '저금'),
    )
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=50, help_text="예: 식비, 월급, 보험료")
    type = models.CharField(max_length=10, choices=CATEGORY_TYPE_CHOICES)
    is_fixed = models.BooleanField(default=False, help_text="지출일 경우 고정비(True)인지 변동비(False)인지 구분합니다.", verbose_name="고정비 여부")
    payment_day = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="고정 지출일 또는 급여(수입) 수령일 (1~31). 대시보드 기본 조회 기간 산출에 사용됩니다.",
        verbose_name="지출/수령 일자"
    )
    fixed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        help_text="고정비의 월 예정 지출 금액 (원). 고정비 카테고리에만 입력하세요.",
        verbose_name="고정 금액"
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="고정비 시작일자. 이 날짜부터 대시보드에 예정 검이 표시됩니다.",
        verbose_name="시작일자"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="고정비 종료일자. 비워두면 무기한 지출로 간주합니다.",
        verbose_name="종료일자"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '분류 (Category)'
        verbose_name_plural = '분류 목록 (Categories)'

    def __str__(self):
        prefix = "[고정]" if self.is_fixed else "[변동]"
        return f"{self.get_type_display()} - {prefix} {self.name}" if self.type == 'expense' else f"{self.get_type_display()} - {self.name}"


class Asset(models.Model):
    """
    내 자산 (현금, 은행 통장, 신용카드, 적금 등) 모델.
    이체를 통해 자산 간 현금 흐름을 추적합니다.
    """
    ASSET_TYPE_CHOICES = (
        ('cash', '현금'),
        ('bank', '입출금 통장'),
        ('savings', '저축/적금'),
        ('card', '신용/체크카드'),
        ('pay', '포인트/페이'),
        ('investment', '투자/주식/코인'),
        ('loan', '대출/부채'),
        ('insurance', '보험'),
    )

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='assets')
    name = models.CharField(max_length=50, help_text="예: 농협 월급통장, 신한카드, 청약통장")
    bank_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="은행/카드사명", help_text="예: 농협, 신한카드")
    account_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="계좌번호/카드번호")
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPE_CHOICES, default='bank', verbose_name="자산 유형")
    initial_balance = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="초기 잔액")
    memo = models.TextField(blank=True, null=True, verbose_name="메모", help_text="이 자산에 대한 간략한 메모나 코멘트를 자유롭게 작성해주세요.")
    is_active = models.BooleanField(default=True, verbose_name="사용 여부")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '자산 (Asset)'
        verbose_name_plural = '자산 목록 (Assets)'

    def __str__(self):
        return f"[{self.get_asset_type_display()}] {self.name}"

    @property
    def current_balance(self):
        from django.db.models import Sum
        deposits = self.deposits.filter(is_deleted=False).aggregate(total=Sum('amount'))['total'] or 0
        withdraws = self.withdraws.filter(is_deleted=False).aggregate(total=Sum('amount'))['total'] or 0
        return self.initial_balance + deposits - withdraws


class Transaction(models.Model):
    """
    개별 거래(수입/지출) 내역을 저장하는 모델.
    """
    TRANSACTION_TYPE_CHOICES = (
        ('income', '수입'),
        ('expense', '지출'),
        ('savings_deposit', '저축 넣기(입금)'),
        ('savings_withdraw', '저축 깨기(출금)'),
        ('transfer', '단순 이체'),
    )

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='transactions')
    
    amount = models.DecimalField(max_digits=12, decimal_places=0, help_text="거래 금액 (원)")
    date = models.DateField(help_text="거래 날짜")
    merchant = models.CharField(max_length=100, blank=True, null=True, help_text="사용처 (선택)", verbose_name="사용처")
    description = models.CharField(max_length=255, help_text="내역 내용")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default='expense')
    
    # 새롭게 추가된 외래키 필드 (기존 DB와의 호환성을 위해 null=True 허용)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', help_text="상세 분류")
    
    # 🌟 자산(통장) 관리 핵심 필드
    withdraw_asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name='withdraws', help_text="돈이 빠져나간 통장/카드")
    deposit_asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name='deposits', help_text="돈이 들어온 통장")
    
    image = models.ImageField(upload_to='receipts/%Y/%m/', blank=True, null=True, help_text="영수증 이미지")
    is_deleted = models.BooleanField(
        default=False,
        help_text="삭제 요청 시 True로 표시 (실제 DB에서 제거하지 않음 - 소프트 삭제).",
        verbose_name="삭제 여부"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = '거래 내역 (Transaction)'
        verbose_name_plural = '거래 내역 목록 (Transactions)'
        ordering = ['-date', '-created_at']

    def __str__(self):
        cat_name = self.category.name if self.category else '미분류'
        w_asset = self.withdraw_asset.name if self.withdraw_asset else '-'
        d_asset = self.deposit_asset.name if self.deposit_asset else '-'
        return f"[{self.get_transaction_type_display()}|{cat_name}|{w_asset}->{d_asset}] {self.date} - {self.description} : {self.amount}원"
