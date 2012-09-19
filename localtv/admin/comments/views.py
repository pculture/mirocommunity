from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.contrib.comments.signals import comment_was_flagged
from django.contrib.comments.views import utils
from django.contrib.comments.models import CommentFlag, Comment
from django.contrib.comments.views.moderation import (perform_approve,
                                                      perform_delete)
from django.core.paginator import Paginator, InvalidPage
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect
from django.views.generic import ListView

from localtv.admin.comments.forms import BulkModerateFormSet
from localtv.decorators import require_site_admin


class CommentListView(ListView):
    paginate_by = 50
    model = Comment
    context_object_name = 'comments'
    template_name = 'localtv/admin/comments/list.html'

    def get_queryset(self):
        qs = super(CommentListView, self).get_queryset()
        qs = qs.filter(is_public=False, is_removed=False)
        return qs


@csrf_protect
@permission_required("comments.can_moderate")
def moderation_queue(request):
    qs = Comment.objects.filter(is_public=False, is_removed=False)
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
    }, context_instance=RequestContext(request))


#@require_site_admin
def comments_spam(request, comment_id, next=None):
    """
    Mark a comment as spam. Confirmation on GET, action on POST.

    Templates: `comments/spam.html`,
    Context:
        comment
            the spammed `comments.comment` object
    """
    comment = get_object_or_404(Comment, pk=comment_id, site__pk=settings.SITE_ID)

    # Flag on POST
    if request.method == 'POST':
        flag, created = CommentFlag.objects.get_or_create(
            comment = comment,
            user    = request.user,
            flag    = 'spam'
        )

        comment.is_removed = True
        comment.save()

        comment_was_flagged.send(
            sender  = comment.__class__,
            comment = comment,
            flag    = flag,
            created = created,
            request = request,
        )
        return utils.next_redirect(request.POST.copy(), next, spam_done, c=comment.pk)

    # Render a form on GET
    else:
        return render_to_response('comments/spam.html',
            {'comment': comment, "next": next},
            RequestContext(request)
        )
comments_spam = require_site_admin(comments_spam)

spam_done = utils.confirmation_view(
    template = "comments/spammed.html",
    doc = 'Displays a "comment was marked as spam" success page.'
)

