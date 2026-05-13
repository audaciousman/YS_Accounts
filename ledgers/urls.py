from django.urls import path
from .views import (
    LedgerDashboardView, TransactionCreateView, TransactionUpdateView, TransactionSoftDeleteView, HouseholdSwitchView,
    LedgerSettingsView,
    CategoryCreateView, CategoryUpdateView, CategoryDeleteView,
    AssetCreateView, AssetUpdateView, AssetDeleteView, LedgerStatsView, GroupRequestCreateView, FixedTransactionQuickAddView,
    TransactionBatchCreateView, download_batch_template,
    AssetBatchCreateView, download_asset_batch_template,
    CategoryBatchCreateView, download_category_batch_template,
    HouseholdSettingsUpdateView
)

app_name = 'ledgers'

urlpatterns = [
    # 가계부 메인 대시보드
    path('', LedgerDashboardView.as_view(), name='dashboard'),
    path('household/switch/<int:pk>/', HouseholdSwitchView.as_view(), name='household_switch'),
    path('group/request/', GroupRequestCreateView.as_view(), name='group_request'),
    path('stats/', LedgerStatsView.as_view(), name='stats'),
    path('create/', TransactionCreateView.as_view(), name='transaction_create'),
    path('batch-add/', TransactionBatchCreateView.as_view(), name='transaction_batch_add'),
    path('batch-template/', download_batch_template, name='download_batch_template'),
    path('quick-add/', FixedTransactionQuickAddView.as_view(), name='quick_add'),
    path('<int:pk>/edit/', TransactionUpdateView.as_view(), name='transaction_update'),
    path('<int:pk>/delete/', TransactionSoftDeleteView.as_view(), name='transaction_delete'),

    # 가계부 환경설정
    path('settings/', LedgerSettingsView.as_view(), name='settings'),
    path('settings/household/update/', HouseholdSettingsUpdateView.as_view(), name='household_settings_update'),
    path('settings/category/add/', CategoryCreateView.as_view(), name='category_create'),
    path('settings/category/<int:pk>/edit/', CategoryUpdateView.as_view(), name='category_update'),
    path('settings/category/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category_delete'),
    path('settings/category/batch-add/', CategoryBatchCreateView.as_view(), name='category_batch_add'),
    path('settings/category/batch-template/', download_category_batch_template, name='download_category_batch_template'),
    
    path('settings/asset/add/', AssetCreateView.as_view(), name='asset_create'),
    path('settings/asset/<int:pk>/edit/', AssetUpdateView.as_view(), name='asset_update'),
    path('settings/asset/<int:pk>/delete/', AssetDeleteView.as_view(), name='asset_delete'),
    path('settings/asset/batch-add/', AssetBatchCreateView.as_view(), name='asset_batch_add'),
    path('settings/asset/batch-template/', download_asset_batch_template, name='download_asset_batch_template'),
]
