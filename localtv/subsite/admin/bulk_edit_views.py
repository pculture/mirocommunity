from datetime import datetime

from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from django.forms.formsets import DELETION_FIELD_NAME
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv import models
from localtv.subsite.admin import forms
from localtv.util import sort_header, MockQueryset

try:
    from operator import methodcaller
except ImportError:
    def methodcaller(name):
        def wrapper(obj):
            return getattr(obj, name)()
        return wrapper

@get_sitelocation
@require_site_admin
def bulk_edit(request, sitelocation=None):
    videos = models.Video.objects.filter(
        status=models.VIDEO_STATUS_ACTIVE,
        site=sitelocation.site)

    category = request.GET.get('category', '')
    try:
        category = int(category)
    except ValueError:
        category = ''

    if category != '':
        videos = videos.filter(categories__pk=category).distinct()

    author = request.GET.get('author', '')
    try:
        author = int(author)
    except ValueError:
        author = ''

    if author != '':
        videos = videos.filter(authors__pk=author).distinct()

    search_string = request.GET.get('q', '')
    if search_string != '':
        videos = videos.filter(
            Q(description__icontains=search_string) |
            Q(name__icontains=search_string) |
            Q(tags__name__icontains=search_string) |
            Q(categories__name__icontains=search_string) |
            Q(user__username__icontains=search_string) |
            Q(user__first_name__icontains=search_string) |
            Q(user__last_name__icontains=search_string) |
            Q(video_service_user__icontains=search_string) |
            Q(feed__name__icontains=search_string))

    sort = request.GET.get('sort', 'name')
    if sort.endswith('source'):
        reverse = sort.startswith('-')
        videos = MockQueryset(
            sorted(videos.order_by(sort.replace('source', 'name')),
                   reverse=reverse,
                   key=methodcaller('source_type')))
    else:
        videos = videos.order_by(sort)

    video_paginator = Paginator(videos, 50)
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        page = video_paginator.page(video_paginator.num_pages)

    videos = videos[page.start_index():page.end_index()]

    headers = [
        sort_header('name', 'Video Title', sort),
        sort_header('source', 'Source', sort),
        {'label': 'Categories'},
        sort_header('when_published', 'Date Posted', sort)]

    if request.method == 'POST':
        formset = forms.VideoFormSet(request.POST, request.FILES,
                                     queryset=videos)
        if formset.is_valid():
            for form in list(formset.deleted_forms):
                form.cleaned_data[DELETION_FIELD_NAME] = False
                form.instance.status = models.VIDEO_STATUS_REJECTED
                form.instance.save()
            bulk_edits = formset.extra_forms[0].cleaned_data
            for key in list(bulk_edits.keys()): # get the list because we'll be
                                                # changing the dictionary
                if not bulk_edits[key]:
                    del bulk_edits[key]
            bulk_action = request.POST.get('bulk_action', '')
            if bulk_action:
                bulk_edits['action'] = bulk_action
            if bulk_edits:
                for form in formset.initial_forms:
                    if not form.cleaned_data['bulk']:
                        continue
                    for key, value in bulk_edits.items():
                        if key == 'action': # do something to the video
                            if value == 'delete':
                                form.instance.status = \
                                    models.VIDEO_STATUS_REJECTED
                            elif value == 'unapprove':
                                form.instance.status = \
                                    models.VIDEO_STATUS_UNAPPROVED
                            elif value == 'feature':
                                form.instance.last_featured = datetime.now()
                            elif value == 'unfeature':
                                form.instance.last_featured = None
                        else:
                            form.cleaned_data[key] = value
            formset.forms = formset.initial_forms # get rid of the extra bulk
                                                  # edit form
            formset.can_delete = False
            formset.save()
            path = request.get_full_path()
            if '?' in path:
                return HttpResponseRedirect(path + '&successful')
            else:
                return HttpResponseRedirect(path + '?successful')
    else:
        formset = forms.VideoFormSet(queryset=videos)

    return render_to_response('localtv/subsite/admin/bulk_edit.html',
                              {'formset': formset,
                               'headers': headers,
                               'page': page,
                               'categories': models.Category.objects.filter(
                site=sitelocation.site),
                               'users': User.objects.all()},
                              context_instance=RequestContext(request))
