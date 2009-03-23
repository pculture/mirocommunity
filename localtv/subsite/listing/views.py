from django.views.generic.list_detail import object_list

from localtv import models
from localtv.decorators import get_sitelocation

@get_sitelocation
def index(request, sitelocation=None):
    pass


@get_sitelocation
def new_videos(request, sitelocation=None):
    videos = models.Video.objects.filter(site=sitelocation.site)
    return object_list(
        request=request, queryset=videos,
        paginate_by=15,
        template_name='localtv/subsite/video_listing.html',
        allow_empty=True, template_object_name='video')


