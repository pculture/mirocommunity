# Miro Community
# Copyright 2009 - Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.generic.list_detail import object_list

from localtv.decorators import get_sitelocation, require_site_admin, \
    referrer_redirect
from localtv import models


## -------------------
## Source administration
## -------------------

class MockQueryset(object):

    def __init__(self, objects):
        self.objects = objects

    def _clone(self):
        return self

    def __len__(self):
        return len(self.objects)

    def __iter__(self):
        return iter(self.objects)

    def __getitem__(self, k):
        return self.objects[k]

@require_site_admin
@get_sitelocation
def manage_sources(request, sitelocation=None):
    search_string = request.GET.get('q', '')

    feeds = models.Feed.objects.filter(
        site=sitelocation.site,
        status=models.FEED_STATUS_ACTIVE).extra(select={
            'name__lower': 'LOWER(name)'}).order_by('name__lower')
    searches = models.SavedSearch.objects.filter(
        site=sitelocation.site).extra(select={
            'query_string__lower': 'LOWER(query_string)'}).order_by(
            'query_string__lower')

    if search_string:
        feeds = feeds.filter(Q(feed_url__icontains=search_string) |
                             Q(name__icontains=search_string) |
                             Q(webpage__icontains=search_string) |
                             Q(description__icontains=search_string))
        searches = searches.filter(query_string__icontains=search_string)

    source_filter = request.GET.get('filter')
    if source_filter == 'search':
        queryset = searches
    elif source_filter in ('feed', 'user'):
        q = Q(feed_url__iregex=models.VIDEO_SERVICE_REGEXES[0][1])
        for service, regexp in models.VIDEO_SERVICE_REGEXES[1:]:
            q = q | Q(feed_url__iregex=regexp)
        if source_filter == 'user':
            queryset = feeds.filter(q)
        else:
            queryset = feeds.exclude(q)
    else:
        feeds_list = [(feed.name.lower(), feed)
                      for feed in feeds]
        searches_list = [(search.query_string.lower(), search)
                         for search in searches]
        queryset = MockQueryset(
            [l[1] for l in sorted(feeds_list + searches_list)])

    return object_list(
        request=request, queryset=queryset,
        paginate_by=15,
        template_name='localtv/subsite/admin/feed_page.html',
        allow_empty=True, template_object_name='feed',
        extra_context = {'search_string': search_string,
                         'source_filter': source_filter})




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
def feed_auto_approve(request, sitelocation=None):
    feed = get_object_or_404(
        models.Feed,
        id=request.GET.get('feed_id'),
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
