from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseBadRequest
from vidscraper import metasearch

from localtv.decorators import get_sitelocation
from localtv import models, util


class SearchedVideo():
    pass


@get_sitelocation
def livesearch_page(request, sitelocation=None):
    query_string = request.GET.get('query')
    if not query_string:
        return HttpResponseBadRequest('We require a query!')

    else:
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
         'video_list': results},
        context_instance=RequestContext(request))
