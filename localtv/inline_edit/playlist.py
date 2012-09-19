from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_protect

from localtv.templatetags.editable_widget import editable_widget

from localtv.playlists.forms import PlaylistForm
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
