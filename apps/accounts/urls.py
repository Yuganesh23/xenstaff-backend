from django.urls import path
from apps.accounts.views import (
    RegisterView, LoginView, LogoutView, MeView, SwitchOrganizationView,
    InviteEmployeeView, VerifyActivationTokenView, SetPasswordView
)

urlpatterns = [
    path('register', RegisterView.as_view(), name='auth-register'),
    path('login', LoginView.as_view(), name='auth-login'),
    path('logout', LogoutView.as_view(), name='auth-logout'),
    path('me', MeView.as_view(), name='auth-me'),
    path('switch-organization', SwitchOrganizationView.as_view(), name='auth-switch-org'),
    path('invite', InviteEmployeeView.as_view(), name='auth-invite'),
    path('verify-token', VerifyActivationTokenView.as_view(), name='auth-verify-token'),
    path('set-password', SetPasswordView.as_view(), name='auth-set-password'),
]
