import datetime
import re

from django.core.urlresolvers import reverse
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin, \
    referrer_redirect
from localtv import models, util
from localtv.subsite.admin import forms


VIDEO_SERVICE_TITLES = (
    re.compile(r'Uploads by (.+)'),
    re.compile(r"Vimeo / (.+)'s uploaded videos")
    )

@require_site_admin
@get_sitelocation
def add_feed(request, sitelocation=None):
    def gen():
        yield render_to_response('localtv/subsite/admin/feed_wait.html',
                                 {'feed_url': request.POST.get('feed_url')},
                                 context_instance=RequestContext(request))
        yield add_feed_response(request, sitelocation)
    return util.HttpMixedReplaceResponse(request, gen())


def add_feed_response(request, sitelocation=None):
    page_num = request.POST.get('page')

    add_form = forms.AddFeedForm(request.POST)

    if not add_form.is_valid():
        return HttpResponseBadRequest(add_form['feed_url'].errors.as_text())

    feed_url = add_form.cleaned_data['feed_url']
    parsed_feed = add_form.cleaned_data['parsed_feed']

    title = parsed_feed.feed.get('title')
    if title is None:
        return HttpResponseBadRequest('That URL does not look like a feed.')
    for regexp in VIDEO_SERVICE_TITLES:
        match = regexp.match(title)
        if match:
            title = match.group(1)
            break

    defaults = {
        'name': title,
        'webpage': parsed_feed.feed.get('link', ''),
        'description': parsed_feed.feed.get('summary', ''),
        'when_submitted': datetime.datetime.now(),
        'last_updated': datetime.datetime.now(),
        'status': models.FEED_STATUS_ACTIVE,
        'user': request.user,
        'etag': '',
        'auto_approve': bool(request.POST.get('auto_approve', False))}

    feed, created = models.Feed.objects.get_or_create(
        feed_url=feed_url,
        site=sitelocation.site,
        defaults = defaults)

    if not created:
        for key, value in defaults.items():
            setattr(feed, key, value)
        feed.save()

    feed.update_items()

    if feed.auto_approve:
        reverse_url = reverse('localtv_subsite_list_feed', args=(feed.pk,))
    else:
        reverse_url = reverse('localtv_admin_manage_page')
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
    feed.video_set.all().delete()
    feed.save()

    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
@get_sitelocation
def feed_auto_approve(request, feed_id, sitelocation=None):
    feed = get_object_or_404(
        models.Feed,
        id=feed_id,
        site=sitelocation.site)

    feed.auto_approve = not request.GET.get('disable')
    feed.save()

    return HttpResponse('SUCCESS')

@referrer_redirect
@require_site_admin
@get_sitelocation
def remove_saved_search(request, sitelocation=None):
    search_id = request.GET.get('search_id')
    existing_saved_search = models.SavedSearch.objects.filter(
        site=sitelocation.site,
        pk=search_id)

    if existing_saved_search.count():
        existing_saved_search.delete()
        return HttpResponse('SUCCESS')
    else:
        return HttpResponseBadRequest(
            'Saved search of that query does not exist')
