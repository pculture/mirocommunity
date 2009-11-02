from django import forms
from django.utils.translation import ugettext_lazy as _

from django.contrib.comments.forms import CommentForm as DjangoCommentForm

class CommentForm(DjangoCommentForm):
    email = forms.EmailField(label=_("Email address"),
                             required=False)
