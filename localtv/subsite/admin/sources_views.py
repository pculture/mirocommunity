import re

from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv import models
from localtv.util import sort_header, MockQueryset
from localtv.subsite.admin import forms

VIDEO_SERVICE_TITLES = (
    re.compile(r'Uploads by (.+)'),
    re.compile(r"Vimeo / (.+)'s uploaded videos")
    )


## -------------------
## Source administration
## -------------------

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

    if sort.endswith('type'):
        if sort[0] == '-':
            orm_sort = '-name__lower'
        else:
            orm_sort = 'name__lower'
    else:
        orm_sort = sort
    feeds = models.Feed.objects.filter(
        site=sitelocation.site,
        status=models.FEED_STATUS_ACTIVE).extra(select={
            'name__lower': 'LOWER(name)'}).order_by(orm_sort)
    searches = models.SavedSearch.objects.filter(
        site=sitelocation.site).extra(select={
            'name__lower': 'LOWER(query_string)'}).order_by(
            orm_sort)

    search_string = request.GET.get('q', '')

    if search_string:
        feeds = feeds.filter(Q(feed_url__icontains=search_string) |
                             Q(name__icontains=search_string) |
                             Q(webpage__icontains=search_string) |
                             Q(description__icontains=search_string))
        searches = searches.filter(query_string__icontains=search_string)

    category = request.GET.get('category')
    if category:
        category = get_object_or_404(models.Category, pk=category)
        feeds = feeds.filter(auto_categories=category)
        searches = searches.filter(auto_categories=category)

    author = request.GET.get('author')
    if author:
        author = get_object_or_404(User, pk=author)
        feeds = feeds.filter(auto_authors=author)
        searches = searches.filter(auto_authors=author)

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
        reverse = False
        if orm_sort[0] == '-':
            reverse = True
            orm_sort = orm_sort[1:]
        feeds_list = [(getattr(feed, orm_sort), feed)
                      for feed in feeds]
        searches_list = [(getattr(search, orm_sort), search)
                         for search in searches]
        queryset = [l[1] for l in sorted(feeds_list + searches_list,
                                         reverse=reverse)]

    if sort.endswith('type'):
        reverse = (sort[0] == '-')
        queryset = sorted(queryset,
                          reverse=reverse,
                          key=lambda source: source.source_type().lower())

    paginator = Paginator(queryset, 15)
    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404

    if request.method == 'POST':
        formset = forms.SourceFormset(request.POST,
                                      queryset=MockQueryset(page.object_list))
        if formset.is_valid():
            bulk_edits = formset.extra_forms[0].cleaned_data
            for key in list(bulk_edits.keys()): # get the list because we'll be
                                                # changing the dictionary
                if bulk_edits[key] in ['', None]:
                    del bulk_edits[key]
            bulk_action = request.POST.get('bulk_action', '')
            for form in formset.initial_forms:
                if form.cleaned_data['bulk']:
                    if bulk_action == 'remove':
                        form.instance.delete()
                        continue
                    if bulk_edits:
                        for key, value in bulk_edits.items():
                            form.cleaned_data[key] = value

                # if the categories or authors changed, update unchanged videos
                # to the new values
                old_categories = set(form.instance.auto_categories.all())
                old_authors = set(form.instance.auto_authors.all())
                form.save()
                new_categories = set(form.instance.auto_categories.all())
                new_authors = set(form.instance.auto_authors.all())
                if old_categories != new_categories or \
                        old_authors != new_authors:
                    for v in form.instance.video_set.all():
                        changed = False
                        if set(v.categories.all()) == old_categories:
                            changed = True
                            v.categories = new_categories
                        if set(v.authors.all()) == old_authors:
                            changed = True
                            v.authors = new_authors
                        if changed:
                            v.save()
            for form in formset.deleted_forms:
                form.instance.delete()

            path = request.get_full_path()
            if '?' in path:
                return HttpResponseRedirect(path + '&successful')
            else:
                return HttpResponseRedirect(path + '?successful')
    else:
        formset = forms.SourceFormset(queryset=MockQueryset(page.object_list))

    return render_to_response('localtv/subsite/admin/manage_sources.html',
                              {
            'add_feed_form': forms.AddFeedForm(),
            'page': page,
            'paginator': paginator,
            'headers': headers,
            'search_string': search_string,
            'source_filter': source_filter,
            'categories': models.Category.objects.filter(
                site=sitelocation.site),
            'users': User.objects.all(),
            'successful': 'successful' in request.GET,
            'formset': formset},
                              context_instance=RequestContext(request))
