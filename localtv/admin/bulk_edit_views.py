# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime

from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from django.forms.formsets import DELETION_FIELD_NAME
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_protect

from localtv.decorators import require_site_admin
from localtv import models
from localtv.admin import forms
from localtv.util import SortHeaders

try:
    from operator import methodcaller
except ImportError:
    def methodcaller(name):
        def wrapper(obj):
            return getattr(obj, name)()
        return wrapper

@require_site_admin
@csrf_protect
def bulk_edit(request):
    if ('just_the_author_field' in request.GET and 'video_id' in request.GET):
        # generate just the particular form that the user wants
        template_data = {}
        form_prefix = request.GET['just_the_author_field']
        video = get_object_or_404(models.Video, pk=int(request.GET['video_id']))
        cache_for_form_optimization = {}
        form = forms.BulkEditVideoForm(instance=video, prefix=form_prefix,
                                       cache_for_form_optimization=cache_for_form_optimization)
        template_data['form'] = form
        template = 'localtv/admin/bulk_edit_author_widget.html'
        return render_to_response(template,
                                  template_data,
                                  context_instance=RequestContext(request))

    videos = models.Video.objects.filter(
        status=models.VIDEO_STATUS_ACTIVE,
        site=request.sitelocation.site)
    videos = videos.select_related('feed', 'search', 'site')

    if 'filter' in request.GET:
        filter_type = request.GET['filter']
        if filter_type == 'featured':
            videos = videos.exclude(last_featured=None)
        elif filter_type == 'rejected':
            videos = models.Video.objects.filter(
                status=models.VIDEO_STATUS_REJECTED,
                site=request.sitelocation.site)
        elif filter_type == 'no-attribution':
            videos = videos.filter(authors=None)
        elif filter_type == 'no-category':
            videos = videos.filter(categories=None)

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
            Q(categories__name__icontains=search_string) |
            Q(user__username__icontains=search_string) |
            Q(user__first_name__icontains=search_string) |
            Q(user__last_name__icontains=search_string) |
            Q(video_service_user__icontains=search_string) |
            Q(feed__name__icontains=search_string)).distinct()

    headers = SortHeaders(request, (
            ('Video Title', 'name'),
            ('Source', 'source'),
            ('Categories', None),
            ('Date Published', '-when_published'),
            ('Date Imported', '-when_submitted'),
            ))

    sort = headers.order_by()
    if sort.endswith('source'):
        reverse = sort.startswith('-')
        videos = videos.extra(select={
                'name_lower':'LOWER(localtv_video.name)'})
        videos = videos.order_by(sort.replace('source', 'calculated_source_type'))
    elif sort.endswith('name'):
        videos = videos.extra(select={
                'name_lower':'LOWER(localtv_video.name)'}).order_by(
            sort.replace('name', 'name_lower'))
    else:
        videos = videos.order_by(sort)
    video_paginator = Paginator(videos, 30)
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        page = video_paginator.page(video_paginator.num_pages)

    if request.method == 'POST':
        formset = forms.VideoFormSet(request.POST, request.FILES,
                                     queryset=page.object_list)
        if formset.is_valid():
            tier_prevented_some_action = False
            tier = request.sitelocation.get_tier()
            videos_approved_so_far = 0

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
                    if not form.cleaned_data['BULK']:
                        continue
                    for key, value in bulk_edits.items():
                        if key == 'action': # do something to the video
                            if value == 'delete':
                                form.instance.status = \
                                    models.VIDEO_STATUS_REJECTED
                            elif value == 'approve':
                                if (request.sitelocation.enforce_tiers() and
                                    tier.remaining_videos() <= videos_approved_so_far):
                                    tier_prevented_some_action = True
                                else:
                                    form.instance.status = \
                                        models.VIDEO_STATUS_ACTIVE
                                    videos_approved_so_far += 1
                            elif value == 'unapprove':
                                form.instance.status = \
                                    models.VIDEO_STATUS_UNAPPROVED
                            elif value == 'feature':
                                if form.instance.status != models.VIDEO_STATUS_ACTIVE:
                                    if (request.sitelocation.enforce_tiers() and
                                        tier.remaining_videos() <= videos_approved_so_far):
                                        tier_prevented_some_action = True
                                    else:
                                        form.instance.status = \
                                            models.VIDEO_STATUS_ACTIVE
                                if form.instance.status == models.VIDEO_STATUS_ACTIVE:
                                    form.instance.last_featured = datetime.now()
                            elif value == 'unfeature':
                                form.instance.last_featured = None
                        elif key == 'tags':
                            form.instance.tags = value
                        elif key == 'categories':
                            # categories append, not replace
                            form.cleaned_data[key] = (
                                list(form.cleaned_data[key]) +
                                list(value))
                        elif key == 'authors':
                            form.cleaned_data[key] = value
                        else:
                            setattr(form.instance, key, value)
            formset.forms = formset.initial_forms # get rid of the extra bulk
                                                  # edit form
            formset.can_delete = False
            formset.save()
            path_with_success = None
            if 'successful' in request.GET:
                path_with_success = request.get_full_path()
            else:
                path = request.get_full_path()
                if '?' in path:
                    path_with_success =  path + '&successful'
                else:
                    path_with_success = path + '?successful'

            if tier_prevented_some_action:
                path = path_with_success + '&not_all_actions_done'
            else:
                path = path_with_success

            return HttpResponseRedirect(path)
    else:
        formset = forms.VideoFormSet(queryset=page.object_list)

    return render_to_response('localtv/admin/bulk_edit.html',
                              {'formset': formset,
                               'headers': headers,
                               'search_string': search_string,
                               'page': page,
                               'categories': models.Category.objects.filter(
                site=request.sitelocation.site),
                               'users': User.objects.order_by('username')},
                              context_instance=RequestContext(request))
