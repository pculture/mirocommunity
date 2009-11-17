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

from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from vidscraper import metasearch

from localtv.decorators import get_sitelocation, require_site_admin, \
    referrer_redirect
from localtv import models, util


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

@require_site_admin
@get_sitelocation
def livesearch(request, sitelocation=None):
    if 'query' not in request.GET or 'debug' in request.GET:
        return livesearch_response(request, sitelocation)
    def gen():
        yield render_to_response('localtv/admin/livesearch_wait.html',
                                 {'query_string': request.GET['query']},
                                 context_instance=RequestContext(request))
        yield livesearch_response(request, sitelocation)
    return util.HttpMixedReplaceResponse(request, gen())


def livesearch_response(request, sitelocation):
    query_string, order_by, query_subkey = get_query_components(request)

    results = []
    if query_string:
        results = cache.get(query_subkey)
        if results is None:
            raw_results = util.metasearch_from_querystring(
                query_string, order_by)
            sorted_raw_results = metasearch.intersperse_results(raw_results)
            results = [
                util.MetasearchVideo.create_from_vidscraper_dict(raw_result)
                for raw_result in sorted_raw_results]
            results = util.strip_existing_metasearchvideos(
                results, sitelocation.site)
            cache.add(query_subkey, results)

    is_saved_search = bool(
        models.SavedSearch.objects.filter(
            site=sitelocation.site,
            query_string=query_string).count())

    video_paginator = Paginator(results, 10)

    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        page = video_paginator.page(video_paginator.num_pages)

    current_video = None
    if page.object_list:
        current_video = page.object_list[0]

    return render_to_response(
        'localtv/admin/livesearch_table.html',
        {'current_video': current_video,
         'page_obj': page,
         'video_list': page.object_list,
         'query_string': query_string,
         'order_by': order_by,
         'is_saved_search': is_saved_search,
         'saved_searches': models.SavedSearch.objects.filter(
                site=sitelocation.site)},
        context_instance=RequestContext(request))


@referrer_redirect
@require_site_admin
@get_sitelocation
@get_search_video
def approve(request, search_video, sitelocation=None):
    video = search_video.generate_video_model(sitelocation.site)
    existing_saved_search = models.SavedSearch.objects.filter(
        site=sitelocation.site, query_string=request.GET.get('query'))
    if existing_saved_search.count():
        video.search = existing_saved_search[0]
    else:
        video.user = request.user
    if request.GET.get('feature'):
        video.last_featured = datetime.datetime.now()
    video.save()

    remove_video_from_session(request)

    return HttpResponse('SUCCESS')


@require_site_admin
@get_sitelocation
@get_search_video
def display(request, search_video, sitelocation=None):
    return render_to_response(
        'localtv/admin/video_preview.html',
        {'current_video': search_video},
        context_instance=RequestContext(request))


@referrer_redirect
@require_site_admin
@get_sitelocation
def create_saved_search(request, sitelocation=None):
    query_string = request.GET.get('query')

    if not query_string:
        return HttpResponseBadRequest('must provide a query_string')

    existing_saved_search = models.SavedSearch.objects.filter(
        site=sitelocation.site,
        query_string=query_string)

    if existing_saved_search.count():
        return HttpResponseBadRequest(
            'Saved search of that query already exists')

    saved_search = models.SavedSearch(
        site=sitelocation.site,
        query_string=query_string,
        user=request.user,
        when_created=datetime.datetime.now())

    saved_search.save()

    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
@get_sitelocation
def search_auto_approve(request, search_id, sitelocation=None):
    search = get_object_or_404(
        models.SavedSearch,
        id=search_id,
        site=sitelocation.site)

    search.auto_approve = not request.GET.get('disable')
    search.save()

    return HttpResponse('SUCCESS')
