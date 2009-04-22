import datetime

from django.core.paginator import Paginator
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseBadRequest
from vidscraper import metasearch

from localtv.decorators import get_sitelocation
from localtv import models, util


## ----------
## Decorators
## ----------

def get_search_video(view_func):
    def new_view_func(request, *args, **kwargs):
        query_string = request.GET.get('query')
        order_by = request.GET.get('order_by')
        if not order_by in ('relevant', 'latest'):
            order_by = 'relevant'

        query_subkey = '%s-%s' % (order_by, query_string)
        session_searches = request.session.get('localtv_livesearches')

        if not session_searches or not session_searches.get(query_subkey):
            return HttpResponseBadRequest(
                'No matching livesearch results in your session')

        search_video = None
        for this_result in session_searches.get(query_subkey):
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

@get_sitelocation
def livesearch_page(request, sitelocation=None):
    query_string = request.GET.get('query')
    order_by = request.GET.get('order_by')
    if not order_by in ('relevant', 'latest'):
        order_by = 'relevant'

    query_subkey = '%s-%s' % (order_by, query_string)

    results = []
    if query_string:
        session_livesearches = request.session.get('localtv_livesearches') or {}
        if session_livesearches.get(query_subkey):
            results = session_livesearches[query_subkey]

        else:
            raw_results = util.metasearch_from_querystring(
                query_string, order_by)
            sorted_raw_results = metasearch.unfriendlysort_results(raw_results)
            results = [
                util.MetasearchVideo.create_from_vidscraper_dict(raw_result)
                for raw_result in sorted_raw_results]
            session_livesearches[query_subkey] = results
            request.session['localtv_livesearches'] = session_livesearches
            request.session.save()
        
    current_video = None
    if len(results):
        current_video = results[0]

    is_saved_search = bool(
        models.SavedSearch.objects.filter(
            site=sitelocation,
            query_string=query_string).count())

    return render_to_response(
        'localtv/subsite/admin/livesearch_table.html',
        {'current_video': current_video,
         'video_list': results,
         'query_string': query_string,
         'order_by': order_by,
         'is_saved_search': is_saved_search},
        context_instance=RequestContext(request))


@get_sitelocation
@get_search_video
def approve(request, search_video, sitelocation=None):
    search_video.generate_video_model(sitelocation.site)
    
    return HttpResponse('SUCCESS')


@get_sitelocation
@get_search_video
def display(request, search_video, sitelocation=None):
    return render_to_response(
        'localtv/subsite/admin/video_preview.html',
        {'current_video': search_video},
        context_instance=RequestContext(request))


@get_sitelocation
def create_saved_search(request, sitelocation=None):
    query_string = request.GET.get('query')

    existing_saved_search = models.SavedSearch.objects.filter(
        site=sitelocation,
        query_string=query_string)

    if existing_saved_search.count():
        return HttpResponseBadRequest(
            'Saved search of that query already exists')

    saved_search = models.SavedSearch(
        site=sitelocation,
        query_string=query_string,
        when_created=datetime.datetime.now())

    saved_search.save()

    return HttpResponse('SUCCESS')
