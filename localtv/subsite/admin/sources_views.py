import re

from django.core.paginator import Paginator, InvalidPage
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv import models
from localtv.util import sort_header
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
        self.ordered = True

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
    sort = request.GET.get('sort', 'name__lower')
    headers = [
        sort_header('name__lower', 'Source', sort),
        {'label': 'Categories'},
        {'label': 'User Attribution'},
        sort_header('type', 'Type', sort),
        sort_header('auto_approve', 'Auto Approve', sort)
        ]

    search_string = request.GET.get('q', '')

    feeds = models.Feed.objects.filter(
        site=sitelocation.site,
        status=models.FEED_STATUS_ACTIVE).extra(select={
            'name__lower': 'LOWER(name)'}).order_by('name__lower')
    searches = models.SavedSearch.objects.filter(
        site=sitelocation.site).extra(select={
            'name__lower': 'LOWER(query_string)'}).order_by(
            'name__lower')

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
        queryset = [l[1] for l in sorted(feeds_list + searches_list)]

    paginator = Paginator(queryset, 15)
    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404

    if request.method == 'POST':
        formset = forms.SourceFormset(request.POST,
                                      queryset=MockQueryset(page.object_list))
        if formset.is_valid():
            # XXX bulk edit form
            formset.save()
            return HttpResponseRedirect(request.path)
    else:
        formset = forms.SourceFormset(queryset=MockQueryset(page.object_list))
    formset.forms[0].as_ul()
    return render_to_response('localtv/subsite/admin/manage_sources.html',
                              {
            'page_obj': page,
            'paginator': paginator,
            'headers': headers,
            'search_string': search_string,
            'source_filter': source_filter,
            'formset': formset},
                              context_instance=RequestContext(request))
