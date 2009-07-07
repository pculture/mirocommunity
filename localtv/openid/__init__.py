from django.contrib.auth.models import User

class OpenIdBackend:

    def authenticate(self, openid_user=None):
        """
        We assume that the openid_user has already been externally validated,
        and simply return the appropriate User,
        """
        return openid_user.user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
