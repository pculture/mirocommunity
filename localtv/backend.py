# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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
