# Miro Community
# Copyright 2009 - Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib.auth.models import User
from localtv.models import SiteLocation

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
