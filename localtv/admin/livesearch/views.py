# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
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


from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.http import HttpResponseBadRequest, HttpResponse, Http404
from django.views.generic import ListView, DetailView, View

from localtv.admin.livesearch.forms import LiveSearchForm
from localtv.decorators import require_site_admin, referrer_redirect
from localtv.models import SavedSearch, SiteLocation, Video
from localtv import utils

class LiveSearchSessionMixin(object):
    """
    Provides common functionality for live search views that access the session
    for information on which videos are being viewed.

    """
    form_class = LiveSearchForm

    def get_form(self):
        return self.form_class(self.request.GET)

    def _get_cache_key(self):
        return '%s_exclusions' % self.form._get_cache_key()

    def get_results(self):
        self.form = self.get_form()
        if self.form.is_valid():
            results = list(self.form.get_results())
        else:
            results = []
        if results:
            # For now, we need to fake an id on each video.
            for i, video in enumerate(results, start=1):
                video.id = i
            exclusions = self.get_exclusions(results)
            results = filter(lambda v: (
                    v.file_url not in exclusions['file_urls'] and
                    v.website_url not in exclusions['website_urls']
                    ), results)
        return results

    def get_exclusions(self, results):
        """
        Returns a dictionary containing ``website_urls`` and ``file_urls``
        which should be excluded. Will raise an :exc:`AttributeError` if called
        without ``self.form`` being valid and bound.

        """
        cache_key = self._get_cache_key()
        exclusions = self.request.session.get(cache_key)
        if (exclusions is None or
            exclusions['timestamp'] < datetime.now() - timedelta(0, 300)):
            # Initial session should exclude all videos that already exist
            # on the site.
            website_urls, file_urls = zip(*[(video.website_url, video.file_url)
                                             for video in results])
            exclusions = Video.objects.filter(website_url__in=website_urls,
                                              file_url__in=file_urls
                                             ).values_list('website_url',
                                                           'file_url')
            if exclusions:
                website_urls, file_urls = map(set, zip(*list(exclusions)))
                website_urls.discard('')
                file_urls.discard('')
            else:
                website_urls = file_urls = set()
            exclusions = {
                'timestamp': datetime.now(),
                'website_urls': website_urls,
                'file_urls': file_urls
            }
            self.request.session[cache_key] = exclusions
        return exclusions


class LiveSearchView(LiveSearchSessionMixin, ListView):
    context_object_name = 'video_list'
    template_name = 'localtv/admin/livesearch_table.html'
    paginate_by = 10

    def get_queryset(self):
        return self.get_results()

    def get_context_data(self, **kwargs):
        context = super(LiveSearchView, self).get_context_data(**kwargs)
        try:
            current_video = context['page_obj'].object_list[0]
        except IndexError:
            current_video = None

        current_site = Site.objects.get_current()
        is_saved_search = False
        if self.form.is_valid():
            is_saved_search = SavedSearch.objects.filter(
                                  site=current_site,
                                  query_string=self.form.cleaned_data['q']
                              ).exists()

        context.update({
                'current_video': current_video,
                'form': self.form,
                'is_saved_search': is_saved_search,
                })
        
        # Provided for backwards-compatibility reasons only.
        cleaned_data = getattr(self.form, 'cleaned_data', self.form.initial)
        context.update({
            'order_by': cleaned_data.get('order_by', 'latest'),
            'query_string': cleaned_data.get('q', '')
        })
        return context

livesearch = require_site_admin(LiveSearchView.as_view())


class LiveSearchVideoMixin(LiveSearchSessionMixin):
    def get_object(self, queryset=None):
        """
        Returns a result, or ``None`` if no matching result was found. A
        ValueError will be raised if an invalid ``video_id`` value is found in
        ``request.GET``.

        """
        results = self.get_results()
        video_id = int(self.request.GET['video_id'])

        for result in results:
            if result.id == video_id:
                return result
        return None


class LiveSearchVideoDetailView(LiveSearchVideoMixin, DetailView):
    template_name = 'localtv/admin/video_preview.html'
    context_object_name = 'current_video'

    def get(self, request, **kwargs):
        try:
            self.object = self.get_object()
        except ValueError:
            self.object = None

        if self.object is None:
            raise Http404

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
display = require_site_admin(LiveSearchVideoDetailView.as_view())


class LiveSearchApproveVideoView(LiveSearchVideoMixin, View):
    """
    Marks the chosen video as approved.

    """
    # TODO: Switch this to a post() method.
    def get(self, request, **kwargs):
        try:
            video = self.get_object()
        except ValueError:
            return HttpResponseBadRequest("Invalid video_id parameter.")

        if not self.form.is_valid():
            return HttpResponseBadRequest("Invalid query.")

        if video is None:
            return HttpResponseBadRequest("No video found for that video_id.")

        if not request.GET.get('queue'):
            sitelocation = SiteLocation.objects.get_current()
            if not sitelocation.get_tier().can_add_more_videos():
                return HttpResponse(
                    content="You are over the video limit. You "
                    "will need to upgrade to approve "
                    "that video.", status=402)

        current_site = Site.objects.get_current()
        try:
            saved_search = SavedSearch.objects.get(site=current_site,
                                    query_string=self.form.cleaned_data['q'])
        except SavedSearch.DoesNotExist:
            video.user = request.user
        else:
            video.search = saved_search

        video.status = Video.ACTIVE
        if request.GET.get('feature'):
            video.last_featured = datetime.now()
        elif request.GET.get('queue'):
            video.status = Video.UNAPPROVED
        video.save()

        try:
            user = User.objects.get(username=video.video_service_user)
        except User.DoesNotExist:
            user = User(username=video.video_service_user)
            user.set_unusable_password()
            user.save()
            utils.get_profile_model().objects.create(
                user=user,
                website=video.video_service_url
            )
        video.authors.add(user)

        # Exclude this video from future listings.
        cache_key = self._get_cache_key()
        exclusions = request.session.get(cache_key)
        if exclusions is not None:
            if video.website_url:
                exclusions['website_urls'].add(video.website_url)
            if video.file_url:
                exclusions['file_urls'].add(video.file_url)
            request.session[cache_key] = exclusions

        return HttpResponse('SUCCESS')
approve = referrer_redirect(require_site_admin(
                            LiveSearchApproveVideoView.as_view()))


class SetSearchAutoApprove(DetailView):
    model = SavedSearch

    def get(self, request, **kwargs):
        #TODO: This, too, should be a POST
        search = self.get_object()
        auto_approve = not request.GET.get('disable')
        if auto_approve != search.auto_approve:
            search.auto_approve = auto_approve
            search.save()
        return HttpResponse('SUCCESS')
search_auto_approve = referrer_redirect(require_site_admin(
                            SetSearchAutoApprove.as_view()))


@referrer_redirect
@require_site_admin
def create_saved_search(request):
    query_string = request.GET.get('q')

    if not query_string:
        return HttpResponseBadRequest('must provide a query_string')

    current_site = Site.objects.get_current()
    saved_search_exists = SavedSearch.objects.filter(
        site=current_site,
        query_string=query_string
    ).exists()

    if saved_search_exists:
        return HttpResponseBadRequest(
            'Saved search of that query already exists')

    SavedSearch.objects.create(
        site=current_site,
        query_string=query_string,
        user=request.user,
        when_created=datetime.now()
    )

    return HttpResponse('SUCCESS')
