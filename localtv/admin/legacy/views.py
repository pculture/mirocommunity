import datetime

from django.conf import settings
from django.contrib import comments
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.generic import TemplateView

from localtv.decorators import require_site_admin
from localtv.models import Video, SiteSettings


class IndexView(TemplateView):
    template_name = 'localtv/admin/index.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        site_videos = Video.objects.filter(site=settings.SITE_ID)
        active_site_videos = site_videos.filter(status=Video.PUBLISHED)
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        context.update({
            'total_count': active_site_videos.count(),
            'videos_this_week_count': active_site_videos.filter(
                             when_approved__gt=week_ago).count(),
            'unreviewed_count': site_videos.filter(status=Video.NEEDS_MODERATION
                                          ).count(),
            'comment_count': comments.get_model().objects.filter(
                                                              is_public=False,
                                                              is_removed=False
                                                        ).count()
        })
        return context


index = require_site_admin(IndexView.as_view())


@require_site_admin
def hide_get_started(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('You have to POST to this URL.')
    site_settings = SiteSettings.objects.get_current()
    site_settings.hide_get_started = True
    site_settings.save()
    return HttpResponse("OK")
    
