from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
app_name = "accounts"
urlpatterns = [path("login/", views.SecureLoginView.as_view(), name="login"), path("logout/", auth_views.LogoutView.as_view(), name="logout"), path("profile/", views.profile, name="profile"), path("users/", views.user_management, name="user_management"), path("users/add/", views.user_create, name="user_create"), path("users/<int:pk>/edit/", views.user_update, name="user_update"), path("users/<int:pk>/password/", views.user_password, name="user_password"), path("password-change/", auth_views.PasswordChangeView.as_view(template_name="accounts/password_change.html", success_url="/account/profile/"), name="password_change"), path("password-reset/", auth_views.PasswordResetView.as_view(template_name="accounts/password_reset.html",success_url="/account/password-reset/done/"), name="password_reset"),path("password-reset/done/",auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),name="password_reset_done"),path("reset/<uidb64>/<token>/",auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html",success_url="/account/reset/done/"),name="password_reset_confirm"),path("reset/done/",auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),name="password_reset_complete")]

if settings.ENABLE_PUBLIC_REGISTRATION:
    urlpatterns.append(path("register/", views.register, name="register"))
