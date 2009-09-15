# Miro Community
# Copyright 2009 - Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
                not (scraped_data.get('embed')
                     or (scraped_data.get('file_url')
                         and not scraped_data.get('file_url_is_flaky'))):
            raise forms.ValidationError(
                "Can't get either a file url or embed code for this url")

        if 'file_url' in scraped_data and scraped_data['file_url'] is None:
            scraped_data['file_url'] = ''# None is an invalid value

        return self.cleaned_data


class EmbedSubmitVideoForm(SecondStepSubmitVideoForm):
    website_url = forms.URLField(required=False)
    embed = forms.CharField(widget=forms.Textarea)

class DirectSubmitVideoForm(SecondStepSubmitVideoForm):
    website_url = forms.URLField(required=False)

