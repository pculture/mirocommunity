from django import forms
from django.forms.models import modelformset_factory, BaseModelFormSet
from django.utils.translation import ugettext_lazy as _

from django.conf import settings
from django.contrib import comments
from django.contrib.comments import forms as comment_forms
from django.contrib.comments.views.moderation import (perform_approve,
                                                      perform_delete)

try:
    from recaptcha_django import ReCaptchaField
except ImportError:
    ReCaptchaField = None

Comment = comments.get_model()
    
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
            from localtv.models import SiteSettings # avoid circular import
            if SiteSettings.objects.get_current().user_is_admin(data['user']):
                del self.fields['captcha']

class BulkModerateForm(forms.ModelForm):
    BULK = forms.BooleanField(required=False)
    APPROVE = forms.BooleanField(required=False)
    REMOVE = forms.BooleanField(required=False)

    class Meta:
        fields = ['BULK', 'APPROVE', 'REMOVE']

    def save(self, commit=True):
        if self.cleaned_data['APPROVE']:
            perform_approve(self.formset.request, self.instance)
            self.formset.actions.add(self.instance)
        elif self.cleaned_data['REMOVE']:
            perform_delete(self.formset.request, self.instance)
            self.formset.actions.add(self.instance)

class BaseModerateFormSet(BaseModelFormSet):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.actions = set()
        super(BaseModerateFormSet, self).__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        form = super(BaseModerateFormSet, self)._construct_form(i, **kwargs)
        form.formset = self
        return form

    @property
    def bulk_forms(self):
        for form in self.initial_forms:
            if form.cleaned_data['BULK']:
                yield form

BulkModerateFormSet = modelformset_factory(Comment,
                                          form=BulkModerateForm,
                                          formset=BaseModerateFormSet,
                                          extra=0,
                                          can_delete=False)
