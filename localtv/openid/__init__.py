from django.contrib.auth.models import User, SiteLocation

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

    def get_perm(self, user_obj, perm):
        if user_obj.is_superuser:
            return True

        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        sitelocation = SiteLocation.object.get(site=site)
        return sitelocation.user_is_admin(user_obj)
