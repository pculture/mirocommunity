from django.contrib.auth.backends import ModelBackend
from localtv.models import SiteSettings

class SiteAdminBackend(ModelBackend):

    def get_group_permissions(self, user_obj):
        return []

    def get_all_permissions(self, user_obj):
        return []

    def has_perm(self, user_obj, perm_or_app_label):
        """
        We use this method for both has_perm and has_module_perm since our
        authentication is an on-off switch, not permissions-based.
        """
        if user_obj.is_superuser:
            return True

        site_settings = SiteSettings.objects.get_current()
        return site_settings.user_is_admin(user_obj)

    has_module_perms = has_perm
