from django.urls import path
from .views import SignUpView, ProfileUpdateView, CustomPasswordChangeView, ImpersonateUserView, UnimpersonateUserView

app_name = 'accounts'

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', ProfileUpdateView.as_view(), name='profile_edit'),
    path('password/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('impersonate/<int:pk>/', ImpersonateUserView.as_view(), name='impersonate'),
    path('impersonate/stop/', UnimpersonateUserView.as_view(), name='impersonate_stop'),
]
