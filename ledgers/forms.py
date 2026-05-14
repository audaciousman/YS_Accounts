from django import forms
from django.utils import timezone
from .models import Transaction, Category, Asset, GroupRequest, Household

from django.contrib.auth import get_user_model

User = get_user_model()

class GroupRequestForm(forms.ModelForm):
    member_emails = forms.CharField(
        label="포함할 멤버 이메일",
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': '초대할 사용자의 이메일 주소를 쉼표(,) 혹은 줄바꿈으로 구분하여 입력하세요.\n예: user1@example.com, user2@example.com',
            'class': 'w-full px-4 py-2 border rounded-xl',
            'rows': 3
        }),
        help_text="시스템에 가입된 이메일만 등록 가능합니다. 가입되지 않은 이메일이 포함된 경우 요청이 반려됩니다."
    )

    class Meta:
        model = GroupRequest
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '예: 우리집 가계부', 'class': 'w-full px-4 py-2 border rounded-xl'}),
            'description': forms.Textarea(attrs={'placeholder': '그룹의 목적이나 메모를 적어주세요.', 'class': 'w-full px-4 py-2 border rounded-xl', 'rows': 4}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Household.objects.filter(name=name, household_type='group').exists() or GroupRequest.objects.filter(name=name, status='pending').exists():
            raise forms.ValidationError("이미 동일한 이름의 그룹 가계부가 존재하거나 요청 대기 중입니다.")
        return name

    def clean_member_emails(self):
        emails_text = self.cleaned_data.get('member_emails', '')
        if not emails_text:
            return []
            
        import re
        # 쉼표나 공백, 줄바꿈으로 분리
        raw_emails = re.split(r'[,\s]+', emails_text)
        emails = [e.strip() for e in raw_emails if e.strip()]
        
        valid_users = []
        invalid_emails = []
        
        for email in emails:
            try:
                user = User.objects.get(email=email)
                valid_users.append(user)
            except User.DoesNotExist:
                invalid_emails.append(email)
                
        if invalid_emails:
            raise forms.ValidationError(f"다음 이메일은 가입되어 있지 않습니다: {', '.join(invalid_emails)}")
            
        return valid_users

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            valid_users = self.cleaned_data.get('member_emails', [])
            if valid_users:
                instance.requested_members.set(valid_users)
        return instance

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['parent', 'name', 'type', 'is_fixed', 'payment_day', 'fixed_amount', 'start_date', 'end_date']
        widgets = {
            'parent': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-xl text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-xl text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
            'type': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-xl text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
            'is_fixed': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500'}),
            'payment_day': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-xl text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500', 'min': 1, 'max': 31}),
            'fixed_amount': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-xl text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
            'start_date': forms.DateInput(attrs={'class': 'w-full px-4 py-2 border rounded-xl text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'w-full px-4 py-2 border rounded-xl text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        household = kwargs.pop('household', None)
        super().__init__(*args, **kwargs)
        
        if household:
            # 대분류만 부모로 선택 가능 (자신이 대분류인 것)
            qs = Category.objects.filter(household=household, parent__isnull=True)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk) # 자기 자신을 부모로 선택 방지
            self.fields['parent'].queryset = qs.order_by('type', 'name')
            self.fields['parent'].empty_label = "--- 대분류로 설정 (선택 안함) ---"

class TransactionForm(forms.ModelForm):
    """
    가계부 내역(수입/지출/이체)을 작성할 때 사용하는 입력 폼
    """
    class Meta:
        model = Transaction
        fields = ['date', 'transaction_type', 'category', 'withdraw_asset', 'deposit_asset', 'amount', 'merchant', 'description', 'image']
        
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'merchant': forms.TextInput(attrs={'placeholder': '결제하신 곳이나 사용처를 적어주세요. (예: 쿠팡)'}),
            'description': forms.TextInput(attrs={'placeholder': '상세 내역이나 메모를 적어주세요.'}),
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
            all_cats = Category.objects.filter(household=household).order_by('type', '-is_fixed', 'name')
            
            # 카테고리 계층구조(대분류-소분류)를 optgroup으로 묶기 위한 로직
            grouped_choices = [("", "분류(카테고리) 선택")]
            
            # 1. 대분류별로 소분류들을 매핑
            parent_dict = {}
            for c in all_cats:
                if c.parent_id:
                    if c.parent not in parent_dict:
                        parent_dict[c.parent] = []
                    parent_dict[c.parent].append(c)
                else:
                    if c not in parent_dict:
                        parent_dict[c] = []
            
            # 2. choices 리스트 생성 (Django의 optgroup 형식: ('Group Name', [(value, label), ...]))
            # 정렬: 수입/지출, 그리고 이름순
            for p_cat, children in sorted(parent_dict.items(), key=lambda x: (x[0].type, not x[0].is_fixed, x[0].name)):
                if children:
                    # 소분류가 있는 경우, 대분류 자체를 선택할 수도 있게 포함
                    group_opts = [(p_cat.id, f"[대분류] {p_cat.name}")]
                    for child in children:
                        group_opts.append((child.id, f" ↳ {child.name}"))
                    grouped_choices.append((p_cat.get_type_display() + " - " + p_cat.name, group_opts))
                else:
                    # 소분류가 없는 단일 카테고리는 그룹 없이 표시
                    grouped_choices.append((p_cat.id, p_cat.name))

            self.fields['category'].choices = grouped_choices
            
            self.fields['withdraw_asset'].queryset = Asset.objects.filter(household=household, is_active=True).order_by('name')
            self.fields['deposit_asset'].queryset  = Asset.objects.filter(household=household, is_active=True).order_by('name')
            
            # 빈 값일 때의 플레이스홀더 텍스트 변경
            self.fields['withdraw_asset'].empty_label = "어디서 돈이 빠져나갔나요? (선택)"
            self.fields['deposit_asset'].empty_label  = "어디로 돈이 들어왔나요? (선택)"
