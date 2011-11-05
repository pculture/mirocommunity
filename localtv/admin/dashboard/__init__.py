# Copyright 2010 - Participatory Culture Foundation
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

from django.conf.urls.defaults import url, patterns
from django.utils.translation import ugettext_lazy as _
from django.views.generic import RedirectView

from localtv.admin.base import MiroCommunityAdminSection, registry
from localtv.admin.dashboard.views import DashboardView


class DashboardSection(MiroCommunityAdminSection):
    url_prefix = 'dashboard'
    navigation_text = _('Dashboard')
    urlpatterns = patterns('',
        url(r'^$', DashboardView.as_view(), name='localtv_admin_dashboard'),
    )
    site_admin_required = True
    pages = (
        (_('Dashboard'), 'localtv_admin_dashboard'),
    )


registry.register(DashboardSection)