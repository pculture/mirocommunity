from django import forms
from django.utils.translation import ugettext_lazy as _

from django.conf import settings
from django.contrib.comments import forms as comment_forms

try:
    from recaptcha_django import ReCaptchaField
except ImportError:
    RecaptchaField = None

class CommentForm(comment_forms.CommentForm):
    comment = forms.CharField(label=_("Comment"), widget=forms.Textarea,
                              max_length=comment_forms.COMMENT_MAX_LENGTH)
    email = forms.EmailField(label=_("Email address"),
                             required=False)
    if RecaptchaField and not settings.DEBUG and \
            settings.RECAPTCHA_PRIVATE_KEY:
        captcha = ReCaptchaField()

    def __init__(self, target_object, data=None, initial=None):
        comment_forms.CommentForm.__init__(self, target_object, data, initial)
        if 'captcha' in self.fields and data and 'user' in data:
            from localtv.models import SiteLocation # avoid circular import
            if SiteLocation.objects.get_current().user_is_admin(data['user']):
                del self.fields['captcha']

