import datetime

from django.core.urlresolvers import reverse
from django.forms.fields import url_re
from django.http import (
    HttpResponse, HttpResponseBadRequest, HttpResponseRedirect)
from django.shortcuts import get_object_or_404
from django.views.generic.list_detail import object_list
import feedparser

from localtv.decorators import get_sitelocation, require_site_admin, \
    referrer_redirect
from localtv import models


## -------------------
## Feed administration
## -------------------

@require_site_admin
@get_sitelocation
def feeds_page(request, sitelocation=None):
    feeds = models.Feed.objects.filter(
        site=sitelocation.site,
        status=models.FEED_STATUS_ACTIVE)
    return object_list(
        request=request, queryset=feeds,
        paginate_by=15,
        template_name='localtv/subsite/admin/feed_page.html',
        allow_empty=True, template_object_name='feed')


@require_site_admin
@get_sitelocation
def add_feed(request, sitelocation=None):
    feed_url = request.POST.get('feed_url')
    page_num = request.POST.get('page')

    if not feed_url:
        return HttpResponseBadRequest(
            "You must provide a feed URL")

    if not url_re.match(feed_url):
        return HttpResponseBadRequest(
            "Not a valid feed URL")

    if models.Feed.objects.filter(
            feed_url=feed_url,
            site=sitelocation.site,
            status=models.FEED_STATUS_ACTIVE).count():
        return HttpResponseBadRequest(
            "That feed already exists on this site")

    parsed_feed = feedparser.parse(feed_url)

    feed, created = models.Feed.objects.get_or_create(
        feed_url=feed_url,
        site=sitelocation.site,
        defaults = {
            'name': parsed_feed.feed.get('title', ''),
            'webpage': parsed_feed.feed.get('link', ''),
            'description': parsed_feed.feed.get('summary', ''),
            'when_submitted': datetime.datetime.now(),
            'last_updated': datetime.datetime.now(),
            'status': models.FEED_STATUS_ACTIVE,
            'user': request.user,
            'auto_approve': False})

    if not created:
        feed.status = models.FEED_STATUS_ACTIVE
        feed.user = request.user
        feed.save()

    feed.update_items()
 
    reverse_url = reverse('localtv_admin_feed_page')
    if page_num:
        reverse_url += '?page=' + page_num
    return HttpResponseRedirect(reverse_url)


@referrer_redirect
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


@referrer_redirect
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
