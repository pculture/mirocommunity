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

from django.core.urlresolvers import reverse
from django.views.generic import UpdateView

from localtv.admin.settings.forms import SettingsForm
from localtv.models import SiteLocation


class SettingsUpdateView(UpdateView):
	template_name = 'localtv/admin/settings/update.html'
	form_class = SettingsForm

	def get_object(self):
		return SiteLocation.objects.get_current()

	def get_success_url(self):
		return self.success_url or reverse('localtv_admin_settings')
