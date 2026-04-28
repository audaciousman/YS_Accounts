from django import forms
from django.utils import timezone
from .models import Transaction, Category, Asset

class TransactionForm(forms.ModelForm):
    """
    가계부 내역(수입/지출/이체)을 작성할 때 사용하는 입력 폼
    """
    class Meta:
        model = Transaction
        fields = ['date', 'transaction_type', 'category', 'withdraw_asset', 'deposit_asset', 'amount', 'description', 'image']
        
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'image': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
                'capture': 'camera'
            })
        }

    def __init__(self, *args, **kwargs):
        household = kwargs.pop('household', None)
        super().__init__(*args, **kwargs)
        
        # 새로 추가(생성) 모드일 때, 날짜 필드의 기본값을 '오늘'로 셋팅
        if not self.instance.pk and not self.initial.get('date'):
            self.initial['date'] = timezone.localdate()
            
        # 뷰에서 전달받은 household(가계부) 객체를 사용하여, 해당 가계부 전용 설정만 필터링합니다.
        if household:
            self.fields['category'].queryset = Category.objects.filter(household=household).order_by('type', '-is_fixed', 'name')
            self.fields['withdraw_asset'].queryset = Asset.objects.filter(household=household, is_active=True).order_by('name')
            self.fields['deposit_asset'].queryset  = Asset.objects.filter(household=household, is_active=True).order_by('name')
            
            # 빈 값일 때의 플레이스홀더 텍스트 변경
            self.fields['category'].empty_label       = "분류(카테고리) 선택"
            self.fields['withdraw_asset'].empty_label = "어디서 돈이 빠져나갔나요? (선택)"
            self.fields['deposit_asset'].empty_label  = "어디로 돈이 들어왔나요? (선택)"
