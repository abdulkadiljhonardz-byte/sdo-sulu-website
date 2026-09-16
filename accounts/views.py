import hashlib

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from audit.utils import record_action
from core.permissions import super_admin_required
from core.validators import client_ip
from .forms import (
    ManagedUserCreateForm,
    ManagedUserPasswordForm,
    ManagedUserUpdateForm,
    ProfileForm,
    RegistrationForm,
)
from .models import Role, User
from .roles import synchronize_role_permissions
from notifications.emailing import notify_administrators, send_portal_email


class SecureLoginView(LoginView):
    template_name = "accounts/login.html"
    limit = 5
    window = 15 * 60

    def cache_key(self):
        identifier = f"{client_ip(self.request)}:{self.request.POST.get('username', '').lower()}"
        return "login-attempt:" + hashlib.sha256(identifier.encode()).hexdigest()

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST" and cache.get(self.cache_key(), 0) >= self.limit:
            return render(request, "errors/429.html", status=429)
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        key = self.cache_key()
        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, self.window)
        if attempts == self.limit:
            notify_administrators(
                "SDO Sulu portal security alert",
                f"The login attempt limit was reached for an account identifier from IP {client_ip(self.request)}.",
            )
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self.cache_key())
        if form.get_user().role in {Role.ADMIN, Role.STAFF}:
            synchronize_role_permissions(form.get_user())
        return super().form_valid(form)

def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            record_action(request, "Account created", user, current={"username": user.username})
            return redirect("core:dashboard")
    else: form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    original = {"email": request.user.email, "phone": request.user.phone}
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        record_action(request, "Profile updated", user, previous=original,
                      current={"email": user.email, "phone": user.phone})
        messages.success(request, "Your profile was updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


@super_admin_required
def user_management(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    users = User.objects.exclude(is_superuser=True).order_by("last_name", "first_name", "username")
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )
    if role in Role.values:
        users = users.filter(role=role)
    page = Paginator(users, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "accounts/user_management.html",
        {"page": page, "query": query, "selected_role": role, "roles": Role.choices},
    )


@super_admin_required
def user_create(request):
    form = ManagedUserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        synchronize_role_permissions(user)
        record_action(
            request,
            "Staff account created",
            user,
            current={"username": user.username, "role": user.role, "active": user.is_active},
        )
        messages.success(request, f"Account {user.username} was created.")
        send_portal_email(
            "Your SDO Sulu staff portal account",
            f"An account was created for you with username {user.username}. Sign in at {request.build_absolute_uri('/account/login/')} and use the password-reset option if needed.",
            [user.email],
        )
        return redirect("accounts:user_management")
    return render(request, "accounts/user_form.html", {"form": form, "heading": "Add account"})


@super_admin_required
def user_update(request, pk):
    user = get_object_or_404(User.objects.exclude(is_superuser=True), pk=pk)
    previous = {"role": user.role, "active": user.is_active, "email": user.email}
    form = ManagedUserUpdateForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        synchronize_role_permissions(user)
        record_action(
            request,
            "Staff account updated",
            user,
            previous=previous,
            current={"role": user.role, "active": user.is_active, "email": user.email},
        )
        messages.success(request, f"Account {user.username} was updated.")
        return redirect("accounts:user_management")
    return render(request, "accounts/user_form.html", {"form": form, "heading": f"Edit {user.username}", "managed_user": user})


@super_admin_required
def user_password(request, pk):
    user = get_object_or_404(User.objects.exclude(is_superuser=True), pk=pk)
    form = ManagedUserPasswordForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        record_action(request, "Account password reset by administrator", user)
        messages.success(request, f"Password for {user.username} was updated.")
        return redirect("accounts:user_update", pk=user.pk)
    return render(request, "accounts/user_password.html", {"form": form, "managed_user": user})
