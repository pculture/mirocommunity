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

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import (Http404, HttpResponseRedirect,
                         HttpResponsePermanentRedirect)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from localtv.models import Video, SiteSettings
from localtv.utils import SortHeaders

from localtv.playlists import forms
from localtv.playlists.models import Playlist

def playlist_enabled(func):
    def wrapper(request, *args, **kwargs):
        site_settings = SiteSettings.objects.get_current()
        if not site_settings.playlists_enabled:
            raise Http404
        if site_settings.playlists_enabled == 2 and \
                not request.user_is_admin():
            raise Http404
        return func(request, *args, **kwargs)
    return wrapper

def playlist_authorized(func):
    def wrapper(request, playlist_pk, *args, **kwargs):
        playlist = get_object_or_404(Playlist, pk=playlist_pk)
        if request.user_is_admin() or \
                playlist.user == request.user:
            return func(request, playlist, *args, **kwargs)
        else:
            return redirect_to_login(request.get_full_path())
    return wrapper

def redirect_to_index():
    return HttpResponseRedirect(reverse(index))

@playlist_enabled
@login_required
def index(request):
    """
    Displays the list of playlists for a given user, or the current one if none
    is specified.
    """
    if not request.user.is_authenticated():
        return redirect_to_login(request.get_full_path())

    if request.user_is_admin() and request.GET.get(
        'show', None) in ('all', 'waiting'):
        headers = SortHeaders(request, (
                ('Playlist', 'name'),
                ('Description', None),
                ('Slug', None),
                ('Username', 'user__username'),
                ('Status', None),
                ('Video Count', 'items__count')
                ))
        if request.GET.get('show') == 'all':
            playlists = Playlist.objects.all()
        else:
            playlists = Playlist.objects.filter(
                status=Playlist.WAITING_FOR_MODERATION)
    else:
        headers = SortHeaders(request, (
                ('Playlist', 'name'),
                ('Description', None),
                ('Slug', None),
                ('Status', None),
                ('Video Count', 'items__count')
                ))
        playlists = Playlist.objects.filter(user=request.user)

    if headers.ordering == 'items__count':
        playlists = playlists.annotate(Count('items'))
    playlists = playlists.order_by(headers.order_by())


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
                elif request.POST.get('bulk_action') == 'public':
                    if request.user_is_admin():
                        new_status = Playlist.PUBLIC
                    else:
                        new_status = Playlist.WAITING_FOR_MODERATION
                    for form in formset.bulk_forms:
                        if form.instance.status < Playlist.PUBLIC:
                            form.instance.status = new_status
                            form.instance.save()
                elif request.POST.get('bulk_action') == 'private':
                    for form in formset.bulk_forms:
                        form.instance.status = Playlist.PRIVATE
                        form.instance.save()
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
                    site=SiteSettings.objects.get_current().site,
                    user=request.user))
            if form.is_valid():
                playlist = form.save()
                if video:
                    playlist.add_video(video)
                    return HttpResponseRedirect('%s?playlist=%i' % (
                            video.get_absolute_url(),
                            playlist.pk))
                return HttpResponseRedirect(request.path)

    return render_to_response('localtv/playlists/index.html',
                              {'form': form,
                               'headers': headers,
                               'formset': formset},
                              context_instance=RequestContext(request))


class PlaylistView(ListView):
    allow_empty = True
    context_object_name = 'videos'
    
    def get_paginate_by(self, queryset):
        return 15 if 'count' not in self.kwargs else self.kwargs['count']
    
    def get_queryset(self):
        return self.playlist.video_set
    
    def get_context_data(self, *args, **kwargs):
        context = super(PlaylistView, self).get_context_data(*args, **kwargs)
        context.update({'playlist': self.playlist,
                        'video_url_extra': '?playlist=%i' % self.playlist.pk})
        return context
    
    def get_template_names(self):
        return ('localtv/playlists/view.html', 'localtv/video_listing_playlist.html')
    
    def dispatch(self, request, *args, **kwargs):
        self.playlist = get_object_or_404(Playlist, pk=args[0])
        if self.playlist.status != Playlist.PUBLIC:
            if not request.user_is_admin() and \
                    request.user != self.playlist.user:
                raise Http404
        if request.path != self.playlist.get_absolute_url():
            return HttpResponseRedirect(self.playlist.get_absolute_url())
        return super(PlaylistView, self).dispatch(request, *args, **kwargs)


view = playlist_enabled(PlaylistView.as_view())


@playlist_enabled
@playlist_authorized
def edit(request, playlist):
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

@playlist_enabled
@login_required
def add_video(request, video_pk):
    """
    Requests here add the given video to the list.
    """
    if 'playlist' not in request.POST:
        raise Http404
    video = get_object_or_404(Video, pk=video_pk)
    playlist = get_object_or_404(Playlist, pk=request.POST['playlist'])
    if request.user_is_admin() or \
            playlist.user == request.user:
        playlist.add_video(video)
        return HttpResponseRedirect('%s?playlist=%i' % (
                video.get_absolute_url(), playlist.pk))
    return redirect_to_login()

@playlist_enabled
@playlist_authorized
def public(request, playlist):
    if not playlist.is_public():
        if request.user_is_admin():
            playlist.status = Playlist.PUBLIC
        else:
            playlist.status = Playlist.WAITING_FOR_MODERATION
        playlist.save()
    next = reverse('localtv_playlist_index')
    if request.user_is_admin():
        next = next + '?show=all'
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', next))


@playlist_enabled
@playlist_authorized
def private(request, playlist):
    playlist.status = Playlist.PRIVATE
    playlist.save()
    next = reverse('localtv_playlist_index')
    if request.user_is_admin():
        next = next + '?show=all'
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', next))
