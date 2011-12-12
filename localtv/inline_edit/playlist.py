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

from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_protect

from localtv.templatetags.editable_widget import editable_widget

from localtv.playlists.views import playlist_enabled, playlist_authorized

@playlist_enabled
@playlist_authorized
@csrf_protect
def info(request, playlist):
    edit_form = PlaylistForm(request.POST, instance=playlist)
    if edit_form.is_valid():
        edit_form.save()
        Response = HttpResponse
    else:
        Response = HttpResponseForbidden

    widget = editable_widget(request, playlist, 'info', form=edit_form)
    return Response(widget, content_type='text/html')
