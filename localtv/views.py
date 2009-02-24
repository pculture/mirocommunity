from django.contrib.sites.models import Site
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404

from localtv.decorators import get_sitelocation
from localtv import models


@get_sitelocation
def subsite_index(request, sitelocation=None):
    return render_to_response(
        'localtv/subsite/index.html',
        {'sitelocation': sitelocation})


@get_sitelocation
def view_video(request, video_id, sitelocation=None):
    video = get_object_or_404(models.Video, pk=video_id, site=sitelocation.site)

    return render_to_response(
        'localtv/subsite/view_video.html',
        {'sitelocation': sitelocation,
         'current_video': video})
