from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsernameOrEmailBackend(ModelBackend):
    """Authenticate with either the account username or verified email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if not username or password is None:
            return None

        user_model = get_user_model()
        lookup = {"email__iexact": username} if "@" in username else {"username__iexact": username}
        try:
            user = user_model._default_manager.get(**lookup)
        except user_model.DoesNotExist:
            # Keep password hashing work comparable for unknown accounts.
            user_model().set_password(password)
            return None
        except user_model.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
