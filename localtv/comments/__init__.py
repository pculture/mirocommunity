from django.core.urlresolvers import reverse

from localtv.comments.forms import CommentForm


def get_form():
    return CommentForm


def get_form_target():
    return reverse('comments-post-comment')
