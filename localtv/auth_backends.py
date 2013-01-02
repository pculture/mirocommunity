from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User, Permission

from localtv.models import SiteSettings


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

    def get_group_permissions(self, user_obj, obj=None):
        """
        Gives all permissions to superusers and site admins.
        """
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_group_perm_cache'):
            sitesettings = SiteSettings.objects.get_current()
            if sitesettings.user_is_admin(user_obj):
                perms = Permission.objects.all()
            else:
                perms = Permission.objects.filter(group__user=user_obj)
            perms = perms.values_list('content_type__app_label', 'codename').order_by()
            user_obj._group_perm_cache = set(["%s.%s" % (ct, name) for ct, name in perms])
        return user_obj._group_perm_cache
