from django import forms
from django.utils.html import strip_tags

from localtv import util


class BaseSubmitVideoForm(forms.Form):
    url = forms.URLField()
    tags = forms.CharField(required=False)

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


class SubmitVideoForm(BaseSubmitVideoForm):
    url = forms.URLField()
    tags = forms.CharField(required=False)


class SecondStepSubmitVideoForm(BaseSubmitVideoForm):
    thumbnail_url = forms.CharField(required=False)
    name = forms.CharField(max_length=250)
    description = forms.CharField(widget=forms.widgets.Textarea)

    def set_initial(self, request):
        self.initial['url'] = request.GET['url']
        self.initial['tags'] = request.GET.get('tags')


class ScrapedSubmitVideoForm(SecondStepSubmitVideoForm):
    def clean(self):
        scraped_data = util.get_scraped_data(self.cleaned_data['url'])
        if scraped_data and \
                not (scraped_data.get('embed') or scraped_data.get('file_url')):
            raise forms.ValidationError(
                "Can't get either a file url or embed code for this url")

        return self.cleaned_data


class EmbedSubmitVideoForm(SecondStepSubmitVideoForm):
    website_url = forms.URLField(required=False)
    embed = forms.CharField(widget=forms.Textarea)

class DirectSubmitVideoForm(SecondStepSubmitVideoForm):
    website_url = forms.URLField(required=False)

