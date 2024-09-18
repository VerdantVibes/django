from dj_rest_auth.jwt_auth import get_refresh_view
from dj_rest_auth.views import LoginView, LogoutView, UserDetailsView
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from authentication import views as auth_views

urlpatterns = [
    path("login/", LoginView.as_view(), name="rest_login"),
    path("logout/", LogoutView.as_view(), name="rest_logout"),
    path("user/", UserDetailsView.as_view(), name="rest_user_details"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("token/refresh/", get_refresh_view().as_view(), name="token_refresh"),

    path("get-accounts/", auth_views.AccountListView.as_view(), name="get_accounts"),
    path("add-account/", auth_views.AccountAddView.as_view(), name="add_account"),
    path("enable-disable-account/<int:pk>/",
         auth_views.AccountEnableDisableView.as_view(), name="enable_disable_account"),
    path("change-password/<int:pk>/",
         auth_views.ChangePasswordView.as_view(), name="change_password"),
    path('password-reset/', auth_views.PasswordResetView.as_view(),
         name='password-reset'),
    path('password-reset-confirm/', auth_views.PasswordResetConfirmView.as_view(),
         name='password-reset-confirm'),
    path("delete-user/<int:pk>/",
         auth_views.DeleteUserView.as_view(), name="delete_user"),

    path("tenant/", auth_views.TenantView.as_view(), name="tenant"),
]
