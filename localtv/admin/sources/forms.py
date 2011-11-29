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
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from vidscraper import auto_feed
from vidscraper.errors import CantIdentifyUrl

from localtv.models import Feed, SavedSearch, Category


class SourceUpdateForm(forms.ModelForm):
    thumbnail = forms.ImageField(required=False)
    delete_thumbnail = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(SourceUpdateForm, self).__init__(*args, **kwargs)
        opts = self.instance.__class__._meta
        auto_categories = opts.get_field('auto_categories').formfield(
            queryset=Category.objects.filter(site=Site.objects.get_current()),
            widget=forms.CheckboxSelectMultiple,
            help_text=None
        )
        self.fields['auto_categories'] = auto_categories

        auto_authors = opts.get_field('auto_authors').formfield(
            queryset=User.objects.order_by('username'),
            widget=forms.CheckboxSelectMultiple,
            help_text=None
        )
        self.fields['auto_authors'] = auto_authors

    def save(self, *args, **kwargs):
        thumbnail = self.cleaned_data.get('thumbnail')
        delete_thumbnail = self.cleaned_data.get('delete_thumbnail')

        if delete_thumbnail:
            self.instance.delete_thumbnails()
        elif thumbnail is not None:
            self.instance.save_thumbnail_from_file(thumbnail)
        return super(SourceUpdateForm, self).save(*args, **kwargs)


class FeedCreateForm(forms.ModelForm):
    class Meta:
        model = Feed
        fields = ('feed_url', 'auto_approve')

    def clean_feed_url(self):
        url = self.cleaned_data['feed_url']
        try:
            self._vidscraper_feed = auto_feed(url)
        except CantIdentifyUrl:
            raise ValidationError("%s doesn't seem to be a valid RSS/Atom feed "
                                  "URL" % url)

        return self._vidscraper_feed.url

    def save(self, *args, **kwargs):
        self.instance.name = self.instance.feed_url
        self.instance.site = Site.objects.get_current()
        return super(FeedCreateForm, self).save(*args, **kwargs)


class FeedUpdateForm(SourceUpdateForm):
    class Meta:
        model = Feed
        fields = ('auto_approve', 'auto_categories', 'auto_authors', 'feed_url',
                  'name', 'webpage')


class SearchUpdateForm(SourceUpdateForm):
    class Meta:
        model = SavedSearch
        fields = ('auto_approve', 'auto_categories', 'auto_authors',
                  'query_string')