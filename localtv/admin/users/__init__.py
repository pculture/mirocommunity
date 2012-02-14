# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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

from django.conf.urls.defaults import patterns, url
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from localtv.admin.base import (MiroCommunityAdminSection, CRUDSection,
                                registry, user_registry)
from localtv.admin.users.forms import AdminUserForm
from localtv.admin.users.views import UserProfileUpdateView


class UserSection(CRUDSection):
    model = User
    create_form_class = AdminUserForm
    update_form_class = AdminUserForm


class ProfileSection(MiroCommunityAdminSection):
    url_prefix = 'profile'
    navigation_text = _("Profile")
    update_view_class = UserProfileUpdateView
    root_url_name = 'localtv_admin_profile'

    @property
    def urlpatterns(self):
        urlpatterns = patterns('',
            url(r'^$', self.update_view_class.as_view(),
                name = 'localtv_admin_profile')
        )
        return urlpatterns


registry.register(UserSection)
user_registry.register(ProfileSection)