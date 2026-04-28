from django.urls import path
from .views import (
    LedgerDashboardView, TransactionCreateView, TransactionSoftDeleteView, HouseholdSwitchView,
    LedgerSettingsView,
    CategoryCreateView, CategoryUpdateView, CategoryDeleteView,
    AssetCreateView, AssetDeleteView, LedgerStatsView
)

app_name = 'ledgers'

urlpatterns = [
    # 가계부 메인 대시보드
    path('', LedgerDashboardView.as_view(), name='dashboard'),
    path('household/switch/<int:pk>/', HouseholdSwitchView.as_view(), name='household_switch'),
    path('stats/', LedgerStatsView.as_view(), name='stats'),
    path('create/', TransactionCreateView.as_view(), name='transaction_create'),
    path('<int:pk>/delete/', TransactionSoftDeleteView.as_view(), name='transaction_delete'),

    # 가계부 환경설정
    path('settings/', LedgerSettingsView.as_view(), name='settings'),
    path('settings/category/add/', CategoryCreateView.as_view(), name='category_create'),
    path('settings/category/<int:pk>/edit/', CategoryUpdateView.as_view(), name='category_update'),
    path('settings/category/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category_delete'),
    path('settings/asset/add/', AssetCreateView.as_view(), name='asset_create'),
    path('settings/asset/<int:pk>/delete/', AssetDeleteView.as_view(), name='asset_delete'),
]
