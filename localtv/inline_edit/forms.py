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

from django import forms
from django.contrib.auth.models import User

from tagging.forms import TagField

from localtv import models
from localtv.admin.forms import BulkChecklistField


class FeedNameForm(forms.ModelForm):
    class Meta:
        model = models.Feed
        fields = ('name',)


class FeedAutoCategoriesForm(forms.ModelForm):
    class Meta:
        model = models.Feed
        fields = ('auto_categories',)

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        self.fields['auto_categories'].queryset = \
            self.fields['auto_categories'].queryset.filter(
            site=self.instance.site)


class FeedAutoAuthorsForm(forms.ModelForm):
    class Meta:
        model = models.Feed
        fields = ('auto_authors',)

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)

class VideoNameForm(forms.ModelForm):
    class Meta:
        model = models.Video
        fields = ('name',)

class VideoWhenPublishedForm(forms.ModelForm):
    when_published = forms.DateTimeField(
        required=False,
        help_text='Format: yyyy-mm-dd hh:mm:ss')

    class Meta:
        model = models.Video
        fields = ('when_published',)

class VideoAuthorsForm(forms.ModelForm):
    authors = BulkChecklistField(User.objects,
                                 required=False)
    class Meta:
        model = models.Video
        fields = ('authors',)

class VideoCategoriesForm(forms.ModelForm):
    categories = BulkChecklistField(models.Category.objects,
                                    required=False)
    class Meta:
        model = models.Video
        fields = ('categories',)

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        self.fields['categories'].queryset = \
            self.fields['categories'].queryset.filter(
            site=self.instance.site)

class VideoTagsForm(forms.ModelForm):
    tags = TagField(required=False, widget=forms.Textarea)
    class Meta:
        model = models.Video
        fields = ('tags',)

class VideoDescriptionField(forms.ModelForm):
    class Meta:
        model = models.Video
        fields = ('description',)

class VideoWebsiteUrlField(forms.ModelForm):
    class Meta:
        model = models.Video
        fields = ('website_url',)
