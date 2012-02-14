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

from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site

from localtv.admin.base import CRUDSection, registry
from localtv.admin.pages.forms import FlatPageForm


class FlatPageSection(CRUDSection):
	create_form_class = FlatPageForm
	update_form_class = FlatPageForm

	def get_queryset(self):
		return FlatPage.objects.filter(sites=Site.objects.get_current())


registry.register(FlatPageSection)
