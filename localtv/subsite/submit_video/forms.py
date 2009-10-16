# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

import Image
import urllib

from django import forms
from django.core.files.base import ContentFile
from django.utils.html import strip_tags

from localtv import util

class ImageURLField(forms.URLField):

    def clean(self, value):
        value = forms.URLField.clean(self, value)
        if not self.required and value in ['', None]:
            return value
        content_thumb = ContentFile(urllib.urlopen(value).read())
        try:
            Image.open(content_thumb)
        except IOError:
            raise forms.ValidationError('Not a valid image.')
        else:
            content_thumb.seek(0)
            return content_thumb

class BaseSubmitVideoForm(forms.Form):
    url = forms.URLField(verify_exists=True)
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
    pass

class SecondStepSubmitVideoForm(BaseSubmitVideoForm):
    thumbnail = ImageURLField(required=False)
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

