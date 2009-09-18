import re

from django.db.models import Q
from django.views.generic.list_detail import object_list

from localtv.decorators import get_sitelocation, require_site_admin
from localtv import models
from localtv.subsite.admin import forms


VIDEO_SERVICE_TITLES = (
    re.compile(r'Uploads by (.+)'),
    re.compile(r"Vimeo / (.+)'s uploaded videos")
    )


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
        template_name='localtv/subsite/admin/manage_sources.html',
        allow_empty=True, template_object_name='feed',
        extra_context = {'search_string': search_string,
                         'source_filter': source_filter})
