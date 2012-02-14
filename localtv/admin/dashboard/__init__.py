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

from django.conf.urls.defaults import url, patterns
from django.utils.translation import ugettext_lazy as _
from django.views.generic import RedirectView

from localtv.admin.base import MiroCommunityAdminSection, user_registry
from localtv.admin.dashboard.views import DashboardView


class DashboardSection(MiroCommunityAdminSection):
    url_prefix = 'dashboard'
    navigation_text = _('Dashboard')
    root_url_name = 'localtv_admin_dashboard'

    @property
    def urlpatterns(self):
        urlpatterns = patterns('',
            url(r'^$', self.wrap_view(DashboardView.as_view()),
            name='localtv_admin_dashboard'),
        )
        return urlpatterns


user_registry.register(DashboardSection)