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
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import resolve, Resolver404
from django.conf import settings
from django.db.models import Q
from django.http import (Http404, HttpResponsePermanentRedirect,
                         HttpResponseRedirect, HttpResponse)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.vary import vary_on_headers

import localtv.settings
from localtv.models import Video, Watch, Category, NewsletterSettings, SiteLocation

from localtv.playlists.models import (Playlist, PlaylistItem,
                                      PLAYLIST_STATUS_PUBLIC)


def index(request):
    featured_videos = Video.objects.get_featured_videos()
    popular_videos = Video.objects.get_popular_videos()
    new_videos = Video.objects.get_latest_videos().exclude(
                                            feed__avoid_frontpage=True)

    sitelocation_videos = Video.objects.get_sitelocation_videos()
    recent_comments = comments.get_model().objects.filter(
        site=SiteLocation.objects.get_current().site,
        content_type=ContentType.objects.get_for_model(Video),
        object_pk__in=sitelocation_videos.values_list('pk', flat=True),
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
def view_video(request, video_id, slug=None):
    video = get_object_or_404(Video, pk=video_id,
                              site=SiteLocation.objects.get_current().site)

    if not video.is_active() and not request.user_is_admin():
        raise Http404

    if slug is not None and request.path != video.get_absolute_url():
        return HttpResponsePermanentRedirect(video.get_absolute_url())

    context = {'current_video': video,
               # set edit_video_form to True if the user is an admin for
               # backwards-compatibility
               'edit_video_form': request.user_is_admin()}

    sitelocation = SiteLocation.objects.get_current()
    popular_videos = Video.objects.get_popular_videos()
    
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
                    from localtv.listing.views import category_videos
                    if view == category_videos:
                        try:
                            category_obj = Category.objects.get(
                                slug=args[0],
                                site=sitelocation.site)
                        except Category.DoesNotExist:
                            pass
                        else:
                            if not video.categories.filter(
                                pk=category_obj.pk).count():
                                category_obj = None

        if category_obj is None:
            category_obj = video.categories.all()[0]

        context['category'] = category_obj
        popular_videos = popular_videos.filter(categories=category_obj)

    context['popular_videos'] = popular_videos

    if video.voting_enabled():
        import voting
        user_can_vote = True
        if request.user.is_authenticated():
            MAX_VOTES_PER_CATEGORY = getattr(settings,
                                             'MAX_VOTES_PER_CATEGORY',
                                             3)
            max_votes = video.categories.filter(
                contest_mode__isnull=False).count() * MAX_VOTES_PER_CATEGORY
            votes = voting.models.Vote.objects.filter(
                content_type=ContentType.objects.get_for_model(Video),
                user=request.user).count()
            if votes >= max_votes:
                user_can_vote = False
        context['user_can_vote'] = user_can_vote
        if user_can_vote:
            if 'category' in context and context['category'].contest_mode:
                context['contest_category'] = context['category']
            else:
                context['contest_category'] = video.categories.filter(
                    contest_mode__isnull=False)[0]
            

    if sitelocation.playlists_enabled:
        # showing playlists
        if request.user.is_authenticated():
            if request.user_is_admin() or \
                    sitelocation.playlists_enabled == 1:
                # user can add videos to playlists
                context['playlists'] = Playlist.objects.filter(
                    user=request.user)

        if request.user_is_admin():
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
            except (Playlist.DoesNotExist, ValueError):
                pass
            else:
                if playlist.status == PLAYLIST_STATUS_PUBLIC or \
                        request.user_is_admin() or \
                        request.user.is_authenticated() and \
                        playlist.user_id == request.user.pk:
                    try:
                        context['playlistitem'] = video.playlistitem_set.get(
                            playlist=playlist)
                    except PlaylistItem.DoesNotExist:
                        pass

    Watch.add(request, video)

    return render_to_response(
        'localtv/view_video.html',
        context,
        context_instance=RequestContext(request))

def share_email(request, content_type_pk, object_id):
    from email_share import views, forms
    sitelocation = SiteLocation.objects.get_current()
    return views.share_email(request, content_type_pk, object_id,
                             {'site': sitelocation.site,
                              'sitelocation': sitelocation},
                             form_class = forms.ShareMultipleEmailForm
                             )

def video_vote(request, object_id, direction, **kwargs):
    if not localtv.settings.voting_enabled():
        raise Http404
    import voting.views
    if request.user.is_authenticated() and direction != 'clear':
        video = get_object_or_404(Video, pk=object_id)
        MAX_VOTES_PER_CATEGORY = getattr(settings, 'MAX_VOTES_PER_CATEGORY',
                                         3)
        max_votes = video.categories.filter(
            contest_mode__isnull=False).count() * MAX_VOTES_PER_CATEGORY
        votes = voting.models.Vote.objects.filter(
            content_type=ContentType.objects.get_for_model(Video),
            user=request.user).count()
        if votes >= max_votes:
            return HttpResponseRedirect(video.get_absolute_url())
    return voting.views.vote_on_object(request, Video,
                                       direction=direction,
                                       object_id=object_id,
                                       **kwargs)

def newsletter(request):
    newsletter = NewsletterSettings.objects.get_current()
    if not newsletter.status:
        raise Http404
    elif not newsletter.sitelocation.get_tier().permit_newsletter():
        raise Http404

    return HttpResponse(newsletter.as_html(
            {'preview': True}), content_type='text/html')

