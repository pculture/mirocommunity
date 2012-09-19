from django import forms
from django.conf import settings
from django.contrib.comments import forms as comment_forms
from django.contrib.comments.models import Comment
from django.utils.translation import ugettext_lazy as _

try:
    from recaptcha_django import ReCaptchaField
except ImportError:
    ReCaptchaField = None

from localtv.models import SiteSettings


class CommentForm(comment_forms.CommentForm):
    comment = forms.CharField(label=_("Comment"), widget=forms.Textarea,
                              max_length=comment_forms.COMMENT_MAX_LENGTH)
    email = forms.EmailField(label=_("Email address"),
                             required=False)
    if (ReCaptchaField and not settings.DEBUG and
        getattr(settings, 'RECAPTCHA_PRIVATE_KEY', '')):
        captcha = ReCaptchaField()

    def __init__(self, target_object, data=None, initial=None):
        comment_forms.CommentForm.__init__(self, target_object, data, initial)
        if 'captcha' in self.fields and data and 'user' in data:
            if SiteSettings.objects.get_current().user_is_admin(data['user']):
                del self.fields['captcha']
