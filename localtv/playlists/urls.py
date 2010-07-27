# Copyright 2009 - Participatory Culture Foundation
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

from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.playlists.views',
    (r'^$', 'index', {}, 'localtv_playlist_index'),
    (r'^(\d+)$', 'view', {}, 'localtv_playlist_view'),
    (r'^(\d+)/([\w-]+)/?$', 'view', {}, 'localtv_playlist_view'),
    (r'^edit/(\d+)$', 'edit', {}, 'localtv_playlist_edit'),
    (r'^add/(\d+)$', 'add_video', {}, 'localtv_playlist_add_video'),
)
