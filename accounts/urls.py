from django.urls import path
from .views import SignUpView, ProfileUpdateView, CustomPasswordChangeView

app_name = 'accounts'

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', ProfileUpdateView.as_view(), name='profile_edit'),
    path('password/', CustomPasswordChangeView.as_view(), name='password_change'),
]
