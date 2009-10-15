# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib.auth.models import User
from localtv.models import SiteLocation

class OpenIdBackend:

    def authenticate(self, openid_user=None, username=None, password=None):
        """
        If we get an openid_userassume that the openid_user has already been
        externally validated, and simply return the appropriate User,

        Otherwise, we check the username and password against the django.auth
        system.
        """
        if openid_user is not None:
            return openid_user.user

        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

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

        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        sitelocation = SiteLocation.objects.get(site=site)
        return sitelocation.user_is_admin(user_obj)

    has_module_perms = has_perm
