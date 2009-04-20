from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseBadRequest
from vidscraper import metasearch

from localtv.decorators import get_sitelocation
from localtv import util


@get_sitelocation
def livesearch_page(request, sitelocation=None):
    query_string = request.GET.get('query')
    results = []
    if query_string:
        session_livesearches = request.session.get('localtv_livesearches') or {}
        if session_livesearches.get(query_string):
            results = session_livesearches[query_string]

        else:
            raw_results = util.metasearch_from_querystring(query_string)
            sorted_raw_results = metasearch.unfriendlysort_results(raw_results)
            results = [
                util.MetasearchVideo.create_from_vidscraper_dict(raw_result)
                for raw_result in sorted_raw_results]
            session_livesearches[query_string] = results
            request.session['localtv_livesearches'] = session_livesearches
            request.session.save()
        
    current_video = None
    if len(results):
        current_video = results[0]

    return render_to_response(
        'localtv/subsite/admin/approve_reject_table.html',
        {'current_video': current_video,
         'video_list': results,
         'query_string': query_string},
        context_instance=RequestContext(request))


@get_sitelocation
def approve(request, sitelocation=None):
    query_string = request.GET.get('query')
    session_searches = request.session.get('localtv_livesearches')

    if not session_searches or not session_searches.get(query_string):
        return HttpResponseBadRequest(
            'No matching livesearch results in your session')

    search_video = None
    for this_result in session_searches.get(query_string):
        if this_result.id == int(request.GET['video_id']):
            search_video = this_result
            break

    search_video.generate_video_model(sitelocation.site)
    
    return HttpResponse('SUCCESS')
