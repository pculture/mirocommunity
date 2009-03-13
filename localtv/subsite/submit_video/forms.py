from os import path
import urlparse

from django import forms

from localtv import models
from localtv import util


# common cleaning methods
def clean_tags(self):
    tags = []
    for tag_text in self.cleaned_data['tags'].strip().split(','):
        # make sure there's only one space in each tag
        cleaned_tag = ' '.join(tag_text.strip().split())
        if len(cleaned_tag) > 25:
            raise forms.ValidationError(
                'Tags cannot be greater than 25 characters in length')
        tags.append(cleaned_tag)

    return tags


class SubmitVideoForm(forms.Form):
    url = forms.URLField()
    tags = forms.CharField(required=False)

    clean_tags = clean_tags

class ScrapedSubmitVideoForm(forms.Form):
    website_url = forms.URLField()
    tags = forms.CharField()
    file_url = forms.URLField(widget=forms.HiddenInput, required=False)
    embed = forms.CharField(widget=forms.HiddenInput, required=False)
    name = forms.CharField(max_length=250)
    description = forms.CharField(widget=forms.widgets.Textarea)
    #categories = forms.ModelMultipleChoiceField(models.Category.objects.all())

    clean_tags = clean_tags

    def clean_file_url(self):
        if not (self.cleaned_data.get('file_url')
                or self.cleaned_data.get('embed')):
            raise forms.ValidationError(
                'At least one of a file url or embedding code must be provided')

