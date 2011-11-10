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

from localtv.admin.base import MiroCommunityAdminSection, registry
from localtv.admin.settings.views import SettingsUpdateView


class SiteSettingsSection(MiroCommunityAdminSection):
    navigation_text = _("Settings")
    url_prefix = "settings"
    update_view_class = SettingsUpdateView
    site_admin_required = True

    pages = (
    	(_("Settings"), 'localtv_admin_settings'),
    )

    @property
    def urlpatterns(self):
    	urlpatterns = patterns('',
    		url(r'^$', self.update_view_class.as_view(),
    		    name='localtv_admin_settings')
    	)
    	return urlpatterns


registry.register(SiteSettingsSection)
