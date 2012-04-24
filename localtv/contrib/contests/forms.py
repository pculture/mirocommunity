# Copyright 2012 - Participatory Culture Foundation
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

from django import forms
from django.contrib.sites.models import Site

from localtv.contrib.contests.models import Contest


class ContestAdminForm(forms.ModelForm):
	class Meta:
		model = Contest
		exclude = ('videos', 'site',)

	def _post_clean(self):
		super(ContestAdminForm, self)._post_clean()

		if self.instance.site_id is None:
			self.instance.site = Site.objects.get_current()
