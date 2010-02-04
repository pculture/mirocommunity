from django import forms
from django.utils.translation import ugettext_lazy as _

from django.conf import settings
from django.contrib.comments import forms as comment_forms

from recaptcha_django import ReCaptchaField

try:
    from tinymce.widgets import TinyMCE as CommentWidget
except ImportError:
    CommentWidget = forms.Textarea

class CommentForm(comment_forms.CommentForm):
    comment = forms.CharField(label=_("Comment"), widget=CommentWidget,
                              max_length=comment_forms.COMMENT_MAX_LENGTH)
    email = forms.EmailField(label=_("Email address"),
                             required=False)
    if not settings.DEBUG:
        captcha = ReCaptchaField()

    def __init__(self, target_object, data=None):
        comment_forms.CommentForm.__init__(self, target_object, data)
        if not settings.DEBUG and data and 'user' in data:
            from localtv.models import SiteLocation # avoid circular import
            if SiteLocation.objects.get_current().user_is_admin(data['user']):
                del self.fields['captcha']

