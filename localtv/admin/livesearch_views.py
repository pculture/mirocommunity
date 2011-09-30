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

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from vidscraper import metasearch

from localtv import utils
from localtv.decorators import require_site_admin, referrer_redirect
from localtv.models import SiteLocation, Video, SavedSearch
from localtv.admin.utils import MetasearchVideo, metasearch_from_querystring, \
    strip_existing_metasearchvideos

Profile = utils.get_profile_model()

## ----------
## Utils
## ----------

def get_query_components(request):
    """
    Takes a request, and returns a tuple of
    (query_string, order_by, query_subkey)
    """
    query_string = request.GET.get('query', '')
    order_by = request.GET.get('order_by')
    if not order_by in ('relevant', 'latest'):
        order_by = 'latest'

    query_subkey = 'livesearch-%s-%s' % (order_by, hash(query_string))
    return query_string, order_by, query_subkey


def remove_video_from_session(request):
    """
    Removes the video with the video id cfom the session, if it finds it.

    This method does not raise an exception if it isn't found though.
    """
    query_string, order_by, query_subkey = get_query_components(request)

    subkey_videos = cache.get(query_subkey)

    video_index = 0

    for this_result in subkey_videos:
        if this_result.id == int(request.GET['video_id']):
            subkey_videos.pop(video_index)

            cache.set(query_subkey, subkey_videos)
            return
        video_index += 1


## ----------
## Decorators
## ----------

def get_search_video(view_func):
    def new_view_func(request, *args, **kwargs):
        query_string, order_by, query_subkey = get_query_components(request)

        subkey_videos = cache.get(query_subkey)

        if not subkey_videos:
            return HttpResponseBadRequest(
                'No matching livesearch results in your session')

        search_video = None
        for this_result in subkey_videos:
            if this_result.id == int(request.GET['video_id']):
                search_video = this_result
                break

        if not search_video:
            return HttpResponseBadRequest(
                'No specific video matches that id in this queryset')

        return view_func(request, search_video=search_video, *args, **kwargs)

    # make decorator safe
    new_view_func.__name__ = view_func.__name__
    new_view_func.__dict__ = view_func.__dict__
    new_view_func.__doc__ = view_func.__doc__

    return new_view_func


## ----------
## Views
## ----------


@referrer_redirect
@require_site_admin
@get_search_video
def approve(request, search_video):
    sitelocation = SiteLocation.objects.get_current()
    if not request.GET.get('queue'):
        if not sitelocation.get_tier().can_add_more_videos():
            return HttpResponse(content="You are over the video limit. You will need to upgrade to approve that video.", status=402)

    video = search_video.generate_video_model(sitelocation.site)
    existing_saved_search = SavedSearch.objects.filter(
        site=sitelocation.site, query_string=request.GET.get('query'))
    if existing_saved_search.count():
        video.search = existing_saved_search[0]
    else:
        video.user = request.user

    if request.GET.get('feature'):
        video.last_featured = datetime.datetime.now()
    elif request.GET.get('queue'):
        video.status = Video.UNAPPROVED

    user, created = User.objects.get_or_create(
        username=video.video_service_user,
        defaults={'email': ''})
    if created:
        user.set_unusable_password()
        Profile.objects.create(
            user=user,
            website=video.video_service_url)
        user.save()
    video.authors.add(user)
    video.save()

    remove_video_from_session(request)

    return HttpResponse('SUCCESS')


@require_site_admin
@get_search_video
def display(request, search_video):
    return render_to_response(
        'localtv/admin/video_preview.html',
        {'current_video': search_video},
        context_instance=RequestContext(request))


@referrer_redirect
@require_site_admin
def create_saved_search(request):
    query_string = request.GET.get('query')

    if not query_string:
        return HttpResponseBadRequest('must provide a query_string')

    sitelocation = SiteLocation.objects.get_current()
    existing_saved_search = SavedSearch.objects.filter(
        site=sitelocation.site,
        query_string=query_string)

    if existing_saved_search.count():
        return HttpResponseBadRequest(
            'Saved search of that query already exists')

    saved_search = SavedSearch(
        site=sitelocation.site,
        query_string=query_string,
        user=request.user,
        when_created=datetime.datetime.now())

    saved_search.save()

    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
def search_auto_approve(request, search_id):
    search = get_object_or_404(
        SavedSearch,
        id=search_id,
        site=SiteLocation.objects.get_current().site)

    search.auto_approve = not request.GET.get('disable')
    search.save()

    return HttpResponse('SUCCESS')
