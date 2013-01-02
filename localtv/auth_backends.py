from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class MirocommunityBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        """
        Don't try to authenticate users that don't have set passwords - for
        example, users that were created via socialauth. This is needed because
        of how Django-Socialauth works (or doesn't).

        """
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            pass
        else:
            if not user.password:
                user.set_unusable_password()
                user.save()

            if user.check_password(password):
                return user

        return None
