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

from localtv.admin.forms import TagField

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

class SubmitVideoForm(forms.Form):
    url = forms.URLField(verify_exists=True)

class SecondStepSubmitVideoForm(forms.Form):
    url = forms.URLField(verify_exists=True,
                         widget=forms.widgets.HiddenInput)
    name = forms.CharField(max_length=250,
                           label="Video Name")
    thumbnail = ImageURLField(required=False,
                              label="Thumbnail URL (optional)")
    description = forms.CharField(widget=forms.widgets.Textarea,
                                  required=False,
                                  label="Video Description (optional)")
    tags = TagField(required=False, label="Tags (optional)",
                    help_text=("You can also <span class='url'>optionally add "
                               "tags</span> for the video (below)."))
    contact = forms.CharField(max_length=250,
                              label='Contact Info',
                              required=False)

    def clean_description(self):
        return strip_tags(self.cleaned_data['description'])

class ScrapedSubmitVideoForm(forms.Form):
    url = forms.URLField(verify_exists=True,
                         widget=forms.widgets.HiddenInput)
    tags = SecondStepSubmitVideoForm.base_fields['tags']
    contact = SecondStepSubmitVideoForm.base_fields['contact']

class EmbedSubmitVideoForm(SecondStepSubmitVideoForm):
    embed = forms.CharField(widget=forms.Textarea,
                            label="Video <embed> code")

class DirectSubmitVideoForm(SecondStepSubmitVideoForm):
    website_url = forms.URLField(required=False,
                                 label="Original Video Page URL (optional)")
