from django.core.exceptions import PermissionDenied
from accounts.models import Role


def staff_required(view):
    def wrapped(request,*args,**kwargs):
        if not request.user.is_authenticated or not request.user.is_staff_member: raise PermissionDenied
        return view(request,*args,**kwargs)
    return wrapped


def super_admin_required(view):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        if not (request.user.is_superuser or request.user.role == Role.SUPER_ADMIN):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped
