from os import path
import urlparse

from django import forms
from django.utils.html import strip_tags

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


def clean_description(self):
    return strip_tags(self.cleaned_data['description'])


class SubmitVideoForm(forms.Form):
    url = forms.URLField()
    tags = forms.CharField(required=False)

    clean_tags = clean_tags


class ScrapedSubmitVideoForm(forms.Form):
    website_url = forms.URLField()
    tags = forms.CharField(required=False)
    thumbnail_url = forms.CharField(required=False)
    name = forms.CharField(max_length=250)
    description = forms.CharField(widget=forms.widgets.Textarea)

    clean_tags = clean_tags
    clean_description = clean_description

    def clean(self):
        scraped_data = util.get_scraped_data(self.cleaned_data['website_url'])
        if scraped_data and \
                not (scraped_data.get('embed') or scraped_data.get('file_url')):
            raise forms.ValidationError(
                "Can't get either a file url or embed code for this url")

        return self.cleaned_data
