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

import datetime
from django.contrib import comments
from django.core.urlresolvers import resolve, Resolver404
from django.db.models import Q
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.vary import vary_on_headers


from localtv import models
from localtv.decorators import get_sitelocation
from localtv.listing import views as listing_views

from localtv.playlists.models import (Playlist, PlaylistItem,
                                      PLAYLIST_STATUS_PUBLIC)

@get_sitelocation
def index(request, sitelocation=None):
    featured_videos = models.Video.objects.filter(
        site=sitelocation.site_id,
        status=models.VIDEO_STATUS_ACTIVE,
        last_featured__isnull=False)
    featured_videos = featured_videos.order_by(
        '-last_featured', '-when_approved', '-when_published',
        '-when_submitted')

    popular_videos = models.Video.objects.popular_since(
        datetime.timedelta(days=7), sitelocation=sitelocation,
        status=models.VIDEO_STATUS_ACTIVE)

    new_videos = models.Video.objects.new(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)

    recent_comments = comments.get_model().objects.filter(
        site=sitelocation.site,
        is_removed=False,
        is_public=True).order_by('-submit_date')

    return render_to_response(
        'localtv/index.html',
        {'featured_videos': featured_videos,
         'popular_videos': popular_videos,
         'new_videos': new_videos,
         'comments': recent_comments},
        context_instance=RequestContext(request))


def about(request):
    return render_to_response(
        'localtv/about.html',
        {}, context_instance=RequestContext(request))


@vary_on_headers('User-Agent', 'Referer')
@get_sitelocation
def view_video(request, video_id, slug=None, sitelocation=None):
    video = get_object_or_404(models.Video, pk=video_id,
                              site=sitelocation.site)

    if video.status != models.VIDEO_STATUS_ACTIVE and \
            not sitelocation.user_is_admin(request.user):
        raise Http404

    if slug is not None and request.path != video.get_absolute_url():
        return HttpResponsePermanentRedirect(video.get_absolute_url())

    context = {'current_video': video,
               # set edit_video_form to True if the user is an admin for
               # backwards-compatibility
               'edit_video_form': sitelocation.user_is_admin(request.user)}

    if video.categories.count():
        category_obj = None
        referrer = request.META.get('HTTP_REFERER')
        host = request.META.get('HTTP_HOST')
        if referrer and host:
            if referrer.startswith('http://') or \
                    referrer.startswith('https://'):
                referrer = referrer[referrer.index('://')+3:]
            if referrer.startswith(host):
                referrer = referrer[len(host):]
                try:
                    view, args, kwargs = resolve(referrer)
                except Resolver404:
                    pass
                else:
                    if view == listing_views.category:
                        try:
                            category_obj = models.Category.objects.get(
                                slug=args[0],
                                site=sitelocation.site)
                        except models.Category.DoesNotExist:
                            pass
                        else:
                            if not video.categories.filter(
                                pk=category_obj.pk).count():
                                category_obj = None

        if category_obj is None:
            category_obj = video.categories.all()[0]

        context['category'] = category_obj
        context['popular_videos'] = models.Video.objects.popular_since(
            datetime.timedelta(days=7),
            sitelocation=sitelocation,
            status=models.VIDEO_STATUS_ACTIVE,
            categories__pk=category_obj.pk)
    else:
        context['popular_videos'] = models.Video.objects.popular_since(
            datetime.timedelta(days=7),
            sitelocation=sitelocation,
            status=models.VIDEO_STATUS_ACTIVE)

    if sitelocation.playlists_enabled:
        # showing playlists
        user_is_admin = sitelocation.user_is_admin(request.user)
        if request.user.is_authenticated():
            if user_is_admin or sitelocation.playlists_enabled == 1:
                # user can add videos to playlists
                context['playlists'] = Playlist.objects.filter(
                    user=request.user)

        if user_is_admin:
            # show all playlists
            context['playlistitem_set'] = video.playlistitem_set.all()
        elif request.user.is_authenticated():
            # public playlists or my playlists
            context['playlistitem_set'] = video.playlistitem_set.filter(
                Q(playlist__status=PLAYLIST_STATUS_PUBLIC) |
                Q(playlist__user=request.user))
        else:
            # just public playlists
            context['playlistitem_set'] = video.playlistitem_set.filter(
                playlist__status=PLAYLIST_STATUS_PUBLIC)

        if 'playlist' in request.GET:
            try:
                playlist = Playlist.objects.get(pk=request.GET['playlist'])
            except Playlist.DoesNotExist:
                pass
            else:
                if playlist.status == PLAYLIST_STATUS_PUBLIC or \
                        request.user.is_authenticated() and \
                        playlist.user_id == request.user.pk:
                    try:
                        context['playlistitem'] = video.playlistitem_set.get(
                            playlist=playlist)
                    except PlaylistItem.DoesNotExist:
                        pass

    models.Watch.add(request, video)

    return render_to_response(
        'localtv/view_video.html',
        context,
        context_instance=RequestContext(request))

@get_sitelocation
def share_email(request, content_type_pk, object_id, sitelocation):
    from email_share import views, forms
    return views.share_email(request, content_type_pk, object_id,
                             {'site': sitelocation.site,
                              'sitelocation': sitelocation},
                             form_class = forms.ShareMultipleEmailForm
                             )
