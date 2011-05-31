# This file is part of Miro Community.
# Copyright (C) 2010, 2011 Participatory Culture Foundation
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

from django import template
from django.contrib.auth.decorators import permission_required
from django.contrib.comments import get_model as get_comment_model
from django.contrib.comments.models import CommentFlag
from django.contrib.comments.views import comments
from django.contrib.comments.views.moderation import (perform_approve,
                                                      perform_delete)
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_protect

from localtv.comments.forms import BulkModerateFormSet

def post_comment(request, next=None):
    POST = request.POST.copy()
    POST['user'] = request.user
    request.POST = POST
    return comments.post_comment(request, next)

@csrf_protect
@permission_required("comments.can_moderate")
def moderation_queue(request):
    """
    Displays a list of unapproved comments to be approved.

    Templates: `comments/moderation_queue.html`
    Context:
        comments
            Comments to be approved (paginated).
        empty
            Is the comment list empty?
        is_paginated
            Is there more than one page?
        results_per_page
            Number of comments per page
        has_next
            Is there a next page?
        has_previous
            Is there a previous page?
        page
            The current page number
        next
            The next page number
        pages
            Number of pages
        hits
            Total number of comments
        page_range
            Range of page numbers

    Originally copied from Django 1.1, since it was removed in Django 1.2.
    """
    qs = get_comment_model().objects.filter(is_public=False, is_removed=False)
    paginator = Paginator(qs, 30)

    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        raise Http404

    try:
        comments_per_page = paginator.page(page)
    except InvalidPage:
        raise Http404

    if request.method == 'POST':
        formset = BulkModerateFormSet(request.POST,
                                      queryset=comments_per_page.object_list,
                                      request=request)
        if formset.is_valid():
            formset.save()
            if request.POST.get('bulk_action'):
                bulk_action = request.POST['bulk_action']
                perform = None
                if bulk_action == 'approve':
                    perform = perform_approve
                elif bulk_action == 'remove':
                    perform = perform_delete
                if perform:
                    for form in formset.bulk_forms:
                        perform(request, form.instance)
                        formset.actions.add(form.instance)
            path = request.path
            undo = '-'.join(str(instance.pk) for instance in formset.actions)
            if undo:
                path = '%s?undo=%s' % (path, undo)
            return HttpResponseRedirect(path)
    else:
        formset = BulkModerateFormSet(queryset=comments_per_page.object_list)


    return render_to_response("comments/moderation_queue.html", {
        'comments' : comments_per_page.object_list,
        'empty' : page == 1 and paginator.count == 0,
        'is_paginated': paginator.num_pages > 1,
        'results_per_page': 100,
        'has_next': comments_per_page.has_next(),
        'has_previous': comments_per_page.has_previous(),
        'page': page,
        'next': page + 1,
        'previous': page - 1,
        'pages': paginator.num_pages,
        'hits' : paginator.count,
        'page_range' : paginator.page_range,
        'page_obj': comments_per_page,
        'formset': formset,
    }, context_instance=template.RequestContext(request))

@csrf_protect
@permission_required("comments.can_moderate")
def undo(request):
    if request.method == 'POST' and 'actions' in request.POST:
        pks = request.POST['actions'].split('-')
        comments = get_comment_model().objects.filter(pk__in=pks)
        # hide the comments
        comments.update(is_public=False)
        # remove flags
        CommentFlag.objects.filter(
            flag__in=(CommentFlag.MODERATOR_DELETION,
                      CommentFlag.MODERATOR_APPROVAL),
            comment__in=comments).delete()
    return HttpResponseRedirect(reverse('comments-moderation-queue'))
