from allauth.account.adapter import DefaultAccountAdapter


class StaffAccountAdapter(DefaultAccountAdapter):
    """Keep Google sign-in limited to staff accounts created by an admin."""

    def is_open_for_signup(self, request):
        return False
