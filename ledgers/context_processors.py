from django.db.models import Q
from .models import Household

def household_context(request):
    """
    모든 템플릿 화면(base.html 등)에서 사용자가 속한 가계부 리스트와
    현재 활성화된 가계부 정보를 즉시 사용할 수 있도록 컨텍스트를 주입합니다.
    """
    if not request.user.is_authenticated:
        return {}
    
    # 자신이 관리자거나 구성원인 모든 가계부
    households = Household.objects.filter(
        Q(admin_user=request.user) | Q(members=request.user)
    ).distinct()
    
    if not households.exists():
        return {}
        
    active_id = request.session.get('active_household_id')
    active_hh = None
    if active_id:
        active_hh = households.filter(id=active_id).first()
    
    # 세션에 없거나 유효하지 않으면 첫 번째 가계부를 기본으로 지정
    if not active_hh:
        active_hh = households.first()
        request.session['active_household_id'] = active_hh.id
        
    return {
        'available_households': households,
        'active_household': active_hh,
    }
