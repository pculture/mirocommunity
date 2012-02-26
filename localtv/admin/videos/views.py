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

from django.views.generic.edit import FormMixin
from localtv.admin.views import MiroCommunityAdminCreateView


class VideoCreateView(MiroCommunityAdminCreateView):
	"""Overrides :meth:`get_form_kwargs` to not include the instance."""
	def get_form_kwargs(self):
		return FormMixin.get_form_kwargs(self)
