# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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

from django.contrib import comments
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import resolve, Resolver404
from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic import TemplateView, DetailView

import localtv.settings
from localtv.models import Video, Watch, Category, NewsletterSettings, SiteSettings
from localtv.search.forms import SortFilterForm
from localtv.search.utils import NormalizedVideoList

from localtv.playlists.models import Playlist, PlaylistItem


MAX_VOTES_PER_CATEGORY = getattr(settings, 'MAX_VOTES_PER_CATEGORY', 3)


class IndexView(TemplateView):
    template_name = 'localtv/index.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        featured_videos = Video.objects.get_featured_videos()
        form = SortFilterForm({'sort': 'popular'})
        form.full_clean()
        popular_videos = form.get_queryset()
        new_videos = Video.objects.get_latest_videos()

        site_settings_videos = Video.objects.get_site_settings_videos()
        recent_comments = comments.get_model().objects.filter(
            site=settings.SITE_ID,
            content_type=ContentType.objects.get_for_model(Video),
            object_pk__in=site_settings_videos.values_list('pk', flat=True),
            is_removed=False,
            is_public=True).order_by('-submit_date')

        context.update({
            'featured_videos': featured_videos,
            'popular_videos': NormalizedVideoList(popular_videos),
            'new_videos': new_videos,
            'comments': recent_comments
        })
        return context


def about(request):
    return render_to_response(
        'localtv/about.html',
        {}, context_instance=RequestContext(request))


class VideoView(DetailView):
    pk_url_kwarg = 'video_id'
    context_object_name = 'current_video'
    template_name = 'localtv/view_video.html'
    model = Video

    def get_queryset(self):
        qs = super(VideoView, self).get_queryset()
        if not self.request.user_is_admin():
            qs = qs.filter(status=Video.ACTIVE)
        return qs.filter(site=settings.SITE_ID)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        abs_url = self.object.get_absolute_url()
        if self.kwargs['slug'] is None or request.path != abs_url:
            return HttpResponseRedirect(abs_url)

        context = self.get_context_data(object=self.object)

        Watch.add(request, self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(VideoView, self).get_context_data(**kwargs)
        context.update({
            # set edit_video_form to True if the user is an admin for
            # backwards-compatibility
            'edit_video_form': self.request.user_is_admin(),
        })

        site_settings = SiteSettings.objects.get_current()
        # Data for generating popular videos list.
        popular_form_data = {'sort': 'popular'}

        try:
            category_obj = self.object.categories.all()[0]
        except IndexError:
            pass
        else:
            # If there are categories, prefer the category that the user
            # just came from the list view of.
            referrer = self.request.META.get('HTTP_REFERER')
            host = self.request.META.get('HTTP_HOST')
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
                        from localtv.urls import category_videos
                        if view == category_videos:
                            try:
                                category_obj = self.object.categories.get(
                                    slug=kwargs['slug'],
                                    site=site_settings.site)
                            except Category.DoesNotExist:
                                pass

            context['category'] = category_obj
            popular_form_data['category'] = [category_obj]

        form = SortFilterForm(popular_form_data)
        form.full_clean()
        popular_videos = form.get_queryset()
        context['popular_videos'] = NormalizedVideoList(popular_videos)

        if self.object.voting_enabled():
            import voting
            user_can_vote = True
            if self.request.user.is_authenticated():
                max_votes = self.object.categories.filter(
                       contest_mode__isnull=False
                   ).count() * MAX_VOTES_PER_CATEGORY
                votes = voting.models.Vote.objects.filter(
                    content_type=ContentType.objects.get_for_model(Video),
                    user=self.request.user).count()
                if votes >= max_votes:
                    user_can_vote = False
            context['user_can_vote'] = user_can_vote
            if user_can_vote:
                if 'category' in context and context['category'].contest_mode:
                    context['contest_category'] = context['category']
                else:
                    context['contest_category'] = (
                        self.object.categories.filter(
                        contest_mode__isnull=False)[0])

        if site_settings.playlists_enabled:
            # showing playlists
            if self.request.user.is_authenticated():
                if self.request.user_is_admin() or \
                        site_settings.playlists_enabled == 1:
                    # user can add videos to playlists
                    context['playlists'] = Playlist.objects.filter(
                        user=self.request.user)

            playlistitem_qs = self.object.playlistitem_set.all()
            if self.request.user_is_admin():
                # show all playlists
                pass
            elif self.request.user.is_authenticated():
                # public playlists or my playlists
                playlistitem_qs = playlistitem_qs.filter(
                                        Q(playlist__status=Playlist.PUBLIC) |
                                        Q(playlist__user=self.request.user))
            else:
                # just public playlists
                playlistitem_qs = playlistitem_qs.filter(
                                            playlist__status=Playlist.PUBLIC)
            context['playlistitem_set'] = playlistitem_qs
            if 'playlist' in self.request.GET:
                try:
                    playlist = Playlist.objects.get(
                                              pk=self.request.GET['playlist'])
                except (Playlist.DoesNotExist, ValueError):
                    pass
                else:
                    if (playlist.is_public() or
                            self.request.user_is_admin() or
                            (self.request.user.is_authenticated() and
                            playlist.user_id == self.request.user.pk)):
                        try:
                            context['playlistitem'] = (
                                self.object.playlistitem_set.get(
                                                           playlist=playlist))
                        except PlaylistItem.DoesNotExist:
                            pass
        return context


def share_email(request, content_type_pk, object_id):
    from email_share import views, forms
    site_settings = SiteSettings.objects.get_current()
    return views.share_email(request, content_type_pk, object_id,
                             {'site': site_settings.site,
                              'site_settings': site_settings},
                             form_class = forms.ShareMultipleEmailForm
                             )


def video_vote(request, object_id, direction, **kwargs):
    if not localtv.settings.voting_enabled():
        raise Http404
    import voting.views
    if request.user.is_authenticated() and direction != 'clear':
        video = get_object_or_404(Video, pk=object_id)
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
    if newsletter.status == NewsletterSettings.DISABLED:
        raise Http404

    return HttpResponse(newsletter.as_html(
            {'preview': True}), content_type='text/html')
