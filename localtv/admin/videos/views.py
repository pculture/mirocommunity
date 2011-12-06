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

from localtv.admin.views import (MiroCommunityAdminCreateView,
								 MiroCommunityAdminUpdateView,
								 MiroCommunityAdminDeleteView)
from localtv.playlists.models import Playlist


class PlaylistMixin(object):
	def get_queryset(self):
		if self.request.user_is_admin():
			return Playlist.objects.all()
		return Playlist.objects.filter(user=self.request.user)


class PlaylistCreateView(PlaylistMixin, MiroCommunityAdminCreateView):
    def get_form_kwargs(self):
        kwargs = super(PlaylistCreateView, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user
        })
        return kwargs


class PlaylistUpdateView(PlaylistMixin, MiroCommunityAdminUpdateView):
	pass


class PlaylistDeleteView(PlaylistMixin, MiroCommunityAdminDeleteView):
	pass
