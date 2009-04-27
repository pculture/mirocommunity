from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.db.models import Q
from django.views.generic.list_detail import object_list

from localtv import models
from localtv.decorators import get_sitelocation


@get_sitelocation
def subsite_index(request, sitelocation=None):
    featured_videos = models.Video.objects.filter(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE,
        last_featured__isnull=False)
    featured_videos = featured_videos.order_by(
        '-last_featured', '-when_submitted')[:10]
    new_videos = models.Video.objects.filter(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)
    new_videos = new_videos.order_by(
        '-when_submitted')[:10]

    return render_to_response(
        'localtv/subsite/index.html',
        {'sitelocation': sitelocation,
         'request': request,
         'featured_videos': featured_videos,
         'new_videos': new_videos},
        context_instance=RequestContext(request))


@get_sitelocation
def view_video(request, video_id, sitelocation=None):
    video = get_object_or_404(models.Video, pk=video_id, site=sitelocation.site)

    return render_to_response(
        'localtv/subsite/view_video.html',
        {'sitelocation': sitelocation,
         'current_video': video,
         'intensedebate_acct': getattr(settings, 'LOCALTV_INTENSEDEBATE_ACCT')},
        context_instance=RequestContext(request))


@get_sitelocation
def video_search(request, sitelocation=None):
    query_string = request.GET.get('query', '')

    if query_string:
        terms = set(query_string.split())

        exclude_terms = set([
                component for component in terms if component.startswith('-')])
        include_terms = terms.difference(exclude_terms)
        stripped_exclude_terms = [term.lstrip('-') for term in exclude_terms]

        videos = models.Video.objects.filter(
            site=sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE)

        for term in include_terms:
            videos = videos.filter(
                Q(description__icontains=term) | Q(name__icontains=term))

        for term in stripped_exclude_terms:
            videos = videos.exclude(
                Q(description__icontains=term) | Q(name__icontains=term))

        return object_list(
            request=request, queryset=videos,
            paginate_by=15,
            template_name='localtv/subsite/video_listing.html',
            allow_empty=True, template_object_name='video')

    else:
        return render_to_response(
            'localtv/subsite/admin/livesearch_table.html', {})

        
