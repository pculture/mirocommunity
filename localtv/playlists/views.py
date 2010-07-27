from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.urlresolvers import reverse
from django.http import (Http404, HttpResponseRedirect,
                         HttpResponsePermanentRedirect,
                         HttpResponse)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.views.generic.list_detail import object_list

from localtv.decorators import get_sitelocation, referrer_redirect
from localtv.models import Video

from localtv.playlists import forms
from localtv.playlists.models import Playlist

def playlist_authorized(func):
    def wrapper(request, playlist_pk, *args, **kwargs):
        playlist = get_object_or_404(Playlist, pk=playlist_pk)
        if kwargs['sitelocation'].user_is_admin(request.user) or \
                playlist.user == request.user:
            return func(request, playlist, *args, **kwargs)
        else:
            return redirect_to_login(request.get_full_path())
    return wrapper

def redirect_to_index():
    return HttpResponseRedirect(reverse(index))

@login_required
@get_sitelocation
def index(request, sitelocation=None):
    """
    Displays the list of playlists for a given user, or the current one if none
    is specified.
    """
    if not request.user.is_authenticated():
        return redirect_to_login(request.get_full_path())

    headers = [
        {'label': 'Playlist'},
        {'label': 'Description'},
        {'label': 'Slug'},
         {'label': 'Video Count'}
        ]

    playlists = Playlist.objects.filter(user=request.user)

    formset = forms.PlaylistFormSet(queryset=playlists)
    form = forms.PlaylistForm()
    if request.method == 'POST':
        if 'form-TOTAL_FORMS' in request.POST: # formset
            formset = forms.PlaylistFormSet(request.POST, queryset=playlists)
            if formset.is_valid():
                formset.save()
                if request.POST.get('bulk_action') == 'delete':
                    for form in formset.bulk_forms:
                        form.instance.delete()
                return HttpResponseRedirect(request.path)
        else:
            video = None
            if 'video' in request.POST and 'name' in request.POST:
                # Adding a new playlist from a video view.  All we get is a
                # name, so make up the slug.
                video = get_object_or_404(Video, pk=request.POST['video'])
                POST = request.POST.copy()
                POST['slug'] = slugify(request.POST['name'])
                POST['description'] = ''
                request.POST = POST
            form = forms.PlaylistForm(request.POST,
                                      instance=Playlist(
                    user=request.user))
            if form.is_valid():
                playlist = form.save()
                if video:
                    playlist.add_video(video)
                return HttpResponseRedirect(request.path)

    return render_to_response('localtv/playlists/index.html',
                              {'form': form,
                               'headers': headers,
                               'formset': formset},
                              context_instance=RequestContext(request))

def view(request, pk, slug=None, count=15):
    """
    Displays the videos of a given playlist.
    """
    playlist = get_object_or_404(Playlist,
                                 pk=pk)
    if request.path != playlist.get_absolute_url():
        return HttpResponsePermanentRedirect(playlist.get_absolute_url())
    return object_list(
        request=request, queryset=playlist.video_set,
        paginate_by=count,
        template_name='localtv/playlists/view.html',
        allow_empty=True,
        template_object_name='video',
        extra_context={'playlist': playlist})


@get_sitelocation
@playlist_authorized
def edit(request, playlist, sitelocation=None):
    """
    POST requests here edit/reorder a given list.
    """
    headers = [
        {'label': 'Video Name'},
        {'label': 'Order'}
        ]
    if request.method != 'POST': # GET
        formset = forms.PlaylistItemFormSet(instance=playlist)
    else:
        formset = forms.PlaylistItemFormSet(request.POST, instance=playlist)
        if formset.is_valid():
            formset.save()
            if request.POST.get('bulk_action') == 'delete':
                for form in formset.bulk_forms:
                    form.instance.delete()
            return HttpResponseRedirect(request.path)

    return render_to_response('localtv/playlists/edit.html',
                                  {'playlist': playlist,
                                   'headers': headers,
                                   'formset': formset},
                              context_instance=RequestContext(request))

@get_sitelocation
@referrer_redirect
@login_required
def add_video(request, video_pk, sitelocation=None):
    """
    Requests here add the given video to the list.
    """
    if 'playlist' not in request.POST:
        raise Http404
    video = get_object_or_404(Video, pk=video_pk)
    playlist = get_object_or_404(Playlist, pk=request.POST['playlist'])
    if sitelocation.user_is_admin(request.user) or \
            playlist.user == request.user:
        playlist.add_video(video)
        if 'HTTP_REFERER' in request.META:
            return HttpResponse('ADDED')
        else:
            return redirect_to_index()
    return redirect_to_login()

