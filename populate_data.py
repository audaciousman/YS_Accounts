import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from ledgers.models import Household, Category, PaymentMethod

def populate():
    households = Household.objects.all()
    for household in households:
        if not Category.objects.filter(household=household).exists():
            print(f"Populating categories for {household.name}")
            Category.objects.bulk_create([
                Category(household=household, name="💰 급여", type="income", is_fixed=False),
                Category(household=household, name="💵 용돈/부수입", type="income", is_fixed=False),
                Category(household=household, name="🏦 금융/이자", type="income", is_fixed=False),
                Category(household=household, name="🏠 주거/통신", type="expense", is_fixed=True),
                Category(household=household, name="🏥 면허/보험/세금", type="expense", is_fixed=True),
                Category(household=household, name="🎓 교육/학원", type="expense", is_fixed=True),
                Category(household=household, name="🍔 식비", type="expense", is_fixed=False),
                Category(household=household, name="🚌 교통/차량", type="expense", is_fixed=False),
                Category(household=household, name="🎁 경조사/선물", type="expense", is_fixed=False),
                Category(household=household, name="☕ 문화/여가", type="expense", is_fixed=False),
                Category(household=household, name="🛍️ 쇼핑/뷰티", type="expense", is_fixed=False),
                Category(household=household, name="기타", type="expense", is_fixed=False),
            ])
            
        if not PaymentMethod.objects.filter(household=household).exists():
            print(f"Populating payment methods for {household.name}")
            PaymentMethod.objects.bulk_create([
                PaymentMethod(household=household, name="💳 신용카드"),
                PaymentMethod(household=household, name="🏧 체크카드"),
                PaymentMethod(household=household, name="💵 현금"),
                PaymentMethod(household=household, name="📱 간편결제(페이)"),
                PaymentMethod(household=household, name="계좌이체"),
            ])
    print("Done")

if __name__ == '__main__':
    populate()
