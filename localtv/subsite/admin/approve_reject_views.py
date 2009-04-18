from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from localtv.decorators import get_sitelocation
from localtv import models
from django.http import HttpResponse, HttpResponseBadRequest


## --------------------
## Video approve/reject
## --------------------

@get_sitelocation
def approve_reject(request, sitelocation=None):
    if request.method == "GET":
        videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED,
            site=sitelocation.site)

        video_paginator = Paginator(videos, 10)

        try:
            page = video_paginator.page(int(request.GET.get('page', 1)))
        except ValueError:
            return HttpResponseBadRequest('Not a page number')
        except EmptyPage:
            return HttpResponseBadRequest(
                'Page number request exceeded available pages')

        current_video = None
        if page.object_list:
            current_video = page.object_list[0]

        return render_to_response(
            'localtv/subsite/admin/approve_reject_table.html',
            {'current_video': current_video,
             'page_obj': page,
             'video_list': page.object_list},
            context_instance=RequestContext(request))
    else:
        pass


@get_sitelocation
def preview_video(request, sitelocation=None):
    current_video = get_object_or_404(
        models.Video,
        id=request.GET['video_id'],
        status=models.VIDEO_STATUS_UNAPPROVED,
        site=sitelocation.site)
    return render_to_response(
        'localtv/subsite/admin/video_preview.html',
        {'current_video': current_video},
        context_instance=RequestContext(request))


@get_sitelocation
def approve_video(request, sitelocation=None):
    current_video = get_object_or_404(
        models.Video,
        id=request.GET['video_id'],
        status=models.VIDEO_STATUS_UNAPPROVED,
        site=sitelocation.site)
    current_video.status = models.VIDEO_STATUS_ACTIVE
    current_video.save()
    return HttpResponse('SUCCESS')
    

@get_sitelocation
def reject_video(request, sitelocation=None):
    current_video = get_object_or_404(
        models.Video,
        id=request.GET['video_id'],
        status=models.VIDEO_STATUS_UNAPPROVED,
        site=sitelocation.site)
    current_video.status = models.VIDEO_STATUS_REJECTED
    current_video.save()
    return HttpResponse('SUCCESS')


