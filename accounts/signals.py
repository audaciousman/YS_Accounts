from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.apps import apps

# CustomUser 모델 객체가 DB에 저장된 직후(post_save)에 이 함수가 실행됩니다.
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_personal_household(sender, instance, created, **kwargs):
    """
    유저가 새롭게 가입(생성)될 때 автоматически 개인 가계부를 만들어주는 로직
    초기 편의를 위해 자주 쓰이는 이모지가 포함된 카테고리와 기본 결제수단도 함께 자동 생성합니다.
    """
    # 초기 데이터 복원(loaddata) 중일 때는 시그널을 실행하지 않습니다.
    if kwargs.get('raw'):
        return

    if created:
        Household = apps.get_model('ledgers', 'Household')
        Category = apps.get_model('ledgers', 'Category')
        Asset = apps.get_model('ledgers', 'Asset')
        
        display_name = instance.first_name if instance.first_name else instance.email.split('@')[0]
        household_name = f"{display_name}의 개인 가계부"
        
        household = Household.objects.create(
            name=household_name,
            household_type='personal',
            admin_user=instance
        )

        # 기본 수입/지출 카테고리 구성 (is_fixed를 통해 고정비 변동비 구분)
        Category.objects.bulk_create([
            Category(household=household, name="💰 급여", type="income", is_fixed=False),
            Category(household=household, name="💵 용돈/부수입", type="income", is_fixed=False),
            Category(household=household, name="🏦 금융/이자", type="income", is_fixed=False),
            # 고정 지출
            Category(household=household, name="🏠 주거/통신", type="expense", is_fixed=True),
            Category(household=household, name="🏥 면허/보험/세금", type="expense", is_fixed=True),
            Category(household=household, name="🎓 교육/학원", type="expense", is_fixed=True),
            # 변동 지출
            Category(household=household, name="🍔 식비", type="expense", is_fixed=False),
            Category(household=household, name="🚌 교통/차량", type="expense", is_fixed=False),
            Category(household=household, name="🎁 경조사/선물", type="expense", is_fixed=False),
            Category(household=household, name="☕ 문화/여가", type="expense", is_fixed=False),
            Category(household=household, name="🛍️ 쇼핑/뷰티", type="expense", is_fixed=False),
            Category(household=household, name="기타", type="expense", is_fixed=False),
            Category(household=household, name="저금", type="savings", is_fixed=False),
        ])

        # 기본 자산 구성
        Asset.objects.bulk_create([
            Asset(household=household, name="💳 기본 신용카드", asset_type='card'),
            Asset(household=household, name="🏧 기본 입출금", asset_type='bank'),
            Asset(household=household, name="💵 현금", asset_type='cash'),
        ])
