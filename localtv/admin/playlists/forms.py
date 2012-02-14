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

from django import forms
from django.core.exceptions import ValidationError

from localtv.playlists.models import Playlist


class PlaylistForm(forms.ModelForm):
    class Meta:
        model = Playlist
        fields = ['name', 'slug', 'description']

    def _post_clean(self):
        self._validate_unique = False
        super(PlaylistForm, self)._post_clean()
        try:
            self.instance.validate_unique()
        except ValidationError, e:
            self._update_errors(e.message_dict)


class PlaylistCreateForm(PlaylistForm):
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(PlaylistCreateForm, self).__init__(*args, **kwargs)

    def _post_clean(self):
        self.instance.user = self.user
        super(PlaylistCreateForm, self)._post_clean()