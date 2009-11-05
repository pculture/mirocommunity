from django import forms
from django.utils.translation import ugettext_lazy as _

from django.contrib.comments import forms as comment_forms

try:
    from tinymce.widgets import TinyMCE as CommentWidget
except ImportError:
    CommentWidget = forms.Textarea

class CommentForm(comment_forms.CommentForm):
    comment = forms.CharField(label=_("Comment"), widget=CommentWidget,
                              max_length=comment_forms.COMMENT_MAX_LENGTH)
    email = forms.EmailField(label=_("Email address"),
                             required=False)
