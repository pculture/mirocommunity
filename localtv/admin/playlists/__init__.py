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

from localtv.admin.base import CRUDSection, registry
from localtv.admin.playlists.forms import PlaylistForm, PlaylistCreateForm
from localtv.admin.playlists.views import (PlaylistCreateView,
                                           PlaylistUpdateView,
                                           PlaylistDeleteView,
                                           PlaylistListView)
from localtv.models import SiteSettings
from localtv.playlists.models import Playlist


class PlaylistCRUDSection(CRUDSection):
    create_form_class = PlaylistCreateForm
    update_form_class = PlaylistForm

    list_view_class = PlaylistListView
    create_view_class = PlaylistCreateView
    update_view_class = PlaylistUpdateView
    delete_view_class = PlaylistDeleteView

    model = Playlist

    def is_available(self, request):
        site_settings = SiteSettings.objects.get_current()

        if site_settings.playlists_enabled == SiteSettings.PLAYLISTS_DISABLED:
            return False

        if (site_settings.playlists_enabled == SiteSettings.PLAYLISTS_ADMIN_ONLY
            and not request.user_is_admin):
            return False

        return True


registry.register(PlaylistCRUDSection)