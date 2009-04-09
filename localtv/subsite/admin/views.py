from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic.list_detail import object_list

from localtv.decorators import get_sitelocation
from localtv import models


@get_sitelocation
def test_table(request, sitelocation=None):
    return render_to_response(
        'localtv/subsite/admin/test_table.html', {})


@get_sitelocation
def approve_reject(request, sitelocation=None):
    if request.method == "GET":
        videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED,
            site=sitelocation.site)
        current_video = None
        if videos.count():
            current_video = videos[0]
        return object_list(
            request=request, queryset=videos,
            paginate_by=15,
            template_name='localtv/subsite/admin/approve_reject_table.html',
            allow_empty=True, template_object_name='video',
            extra_context={'current_video': current_video})
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

