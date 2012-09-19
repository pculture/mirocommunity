from django import forms
from django.forms.models import modelformset_factory, BaseModelFormSet
from django.contrib.comments.models import Comment

from django.contrib.comments.views.moderation import (perform_approve,
                                                      perform_delete)


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
