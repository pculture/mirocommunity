from django import template
from django.contrib.auth.decorators import permission_required
from django.contrib.comments.views import comments
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.shortcuts import render_to_response

def post_comment(request, next=None):
    POST = request.POST.copy()
    POST['user'] = request.user
    request.POST = POST
    return comments.post_comment(request, next)

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

    Copied from Django 1.1, since it was removed in Django 1.2.
    """
    qs = comments.get_model().objects.filter(is_public=False, is_removed=False)
    paginator = Paginator(qs, 100)

    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        raise Http404

    try:
        comments_per_page = paginator.page(page)
    except InvalidPage:
        raise Http404

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
        'page_range' : paginator.page_range
    }, context_instance=template.RequestContext(request))
