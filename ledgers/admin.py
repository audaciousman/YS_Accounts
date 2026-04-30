from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin
from .models import Household, Transaction, GroupRequest

@admin.register(Household)
class HouseholdAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'household_type', 'admin_user', 'created_at')
    list_filter = ('household_type',)
    search_fields = ('name',)


@admin.register(GroupRequest)
class GroupRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'requester', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description', 'requester__email')
    actions = ['approve_requests', 'reject_requests']

    @admin.action(description="선택된 요청을 승인하고 그룹 생성")
    def approve_requests(self, request, queryset):
        approved_count = 0
        for req in queryset.filter(status='pending'):
            # 그룹(Household) 생성
            household = Household.objects.create(
                name=req.name,
                household_type='group',
                admin_user=req.requester
            )
            household.members.add(req.requester)
            for member in req.requested_members.all():
                household.members.add(member)
            # 요청 상태 변경
            req.status = 'approved'
            req.save()
            approved_count += 1
            
        self.message_user(request, f"{approved_count}개의 요청이 승인되어 그룹이 생성되었습니다.")

    @admin.action(description="선택된 요청을 거절")
    def reject_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f"{updated}개의 요청이 거절되었습니다.")


@admin.register(Transaction)
class TransactionAdmin(SimpleHistoryAdmin):
    # 관리자 목록 페이지에 보여줄 필드 설정
    list_display = ('household', 'date', 'transaction_type', 'description', 'amount', 'image_preview')
    list_filter = ('transaction_type', 'date', 'household')
    search_fields = ('description',)
    date_hierarchy = 'date'
    
    # 영수증 이미지 미리보기를 위한 커스텀 메서드
    def image_preview(self, obj):
        if obj.image:
            # 안전하게 HTML 태그를 렌더링하도록 format_html 사용
            return format_html('<img src="{}" style="max-height: 50px; border-radius: 5px;"/>', obj.image.url)
        return "이미지 없음"
    
    # 관리자 페이지 헤더에서 이 컬럼의 이름을 한글로 지정
    image_preview.short_description = '영수증 미리보기'
    
    readonly_fields = ('image_preview_large',)

    # 상세 페이지 레이아웃 설정
    fieldsets = (
        ('기본 정보', {
            'fields': ('household', 'user', 'date', 'transaction_type')
        }),
        ('금액 및 내용', {
            'fields': ('amount', 'description')
        }),
        ('영수증 이미지', {
            'fields': ('image', 'image_preview_large')
        }),
    )

    def image_preview_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 300px; border-radius: 5px;"/>', obj.image.url)
        return "이미지 없음"
    image_preview_large.short_description = '영수증 뷰어'
