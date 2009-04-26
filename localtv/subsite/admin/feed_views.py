from django.shortcuts import get_object_or_404
from django.views.generic.list_detail import object_list

from localtv.decorators import get_sitelocation
from localtv import models
from django.http import HttpResponse


## -------------------
## Feed administration
## -------------------

@require_site_admin
@get_sitelocation
def feeds_page(request, sitelocation=None):
    feeds = models.Feed.objects.filter(
        site=sitelocation.site)
    return object_list(
        request=request, queryset=feeds,
        paginate_by=15,
        template_name='localtv/subsite/admin/feed_page.html',
        allow_empty=True, template_object_name='feed')


@require_site_admin
@get_sitelocation
def feed_stop_watching(request, sitelocation=None):
    feed = get_object_or_404(
        models.Feed,
        id=request.GET.get('feed_id'),
        site=sitelocation.site)

    feed.status = models.FEED_STATUS_REJECTED
    feed.save()

    return HttpResponse('SUCCESS')


@require_site_admin
@get_sitelocation
def feed_auto_approve(request, sitelocation=None):
    feed = get_object_or_404(
        models.Feed,
        id=request.GET.get('feed_id'),
        site=sitelocation.site)

    feed.auto_approve = not request.GET.get('disable')
    feed.save()

    return HttpResponse('SUCCESS')
