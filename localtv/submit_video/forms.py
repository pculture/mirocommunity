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

try:
    from PIL import Image
except ImportError:
    import Image
import urllib

from django import forms
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.conf import settings

from tagging.forms import TagField

from localtv import models
from localtv.util import (quote_unicode_url, get_profile_model,
                          get_or_create_tags)
from localtv.templatetags.filters import sanitize

class ImageURLField(forms.URLField):

    def clean(self, value):
        value = forms.URLField.clean(self, value)
        if not self.required and value in ['', None]:
            return value
        value = quote_unicode_url(value)
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

REQUIRE_EMAIL = getattr(settings, 'LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL', None)
if REQUIRE_EMAIL:
    contact_label = 'E-mail (required)'
    contact_required = True
else:
    contact_label = 'E-mail (optional)'
    contact_required = False

class SecondStepSubmitVideoForm(forms.ModelForm):
    url = forms.URLField(verify_exists=True,
                         widget=forms.widgets.HiddenInput)
    tags = TagField(required=False, label="Tags (optional)",
                    help_text=("You can also <span class='url'>optionally add "
                               "tags</span> for the video (below)."))
    contact = forms.CharField(max_length=250,
                              label=contact_label,
                              required=contact_required)
    notes = forms.CharField(widget=forms.Textarea,
                           label='Notes (optional)',
                           required=False)

    class Meta:
        model = models.Video
        fields = ['tags', 'contact', 'notes']

    def __init__(self, *args, **kwargs):
        self.sitelocation = kwargs.pop('sitelocation', None)
        self.user = kwargs.pop('user', None)
        if self.user and self.user.is_authenticated():
            kwargs.setdefault('initial', {})['contact'] = self.user.email
        forms.ModelForm.__init__(self, *args, **kwargs)
        if self.sitelocation:
            self.instance.site = self.sitelocation.site
        self.instance.status = models.VIDEO_STATUS_UNAPPROVED

    def save(self, **kwargs):
        commit = kwargs.get('commit', True)
        kwargs['commit'] = False
        video = forms.ModelForm.save(self, **kwargs)
        if self.user.is_authenticated():
            video.user = self.user
        if self.sitelocation.user_is_admin(self.user):
            if (not sitelocation.enforce_tiers() or
                self.sitelocation.get_tier().remaining_videos() >= 1):
                video.status = models.VIDEO_STATUS_ACTIVE
        old_m2m = self.save_m2m
        def save_m2m():
            video = self.instance
            if video.status == models.VIDEO_STATUS_ACTIVE:
                # when_submitted isn't set until after the save
                video.when_approved = video.when_submitted
                video.save()
            if video.thumbnail_url and not video.has_thumbnail:
                try:
                    video.save_thumbnail()
                except models.CannotOpenImageUrl:
                    pass # we'll get it later
            if self.cleaned_data.get('tags'):
                video.tags = self.cleaned_data['tags']
            old_m2m()
        if commit:
            video.save()
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return video

class NeedsDataSubmitVideoForm(SecondStepSubmitVideoForm):
    name = forms.CharField(max_length=250,
                           label="Video Name")
    thumbnail_file = forms.ImageField(required=False,
                                     label="Thumbnail File (optional)")
    thumbnail = ImageURLField(required=False,
                              label="Thumbnail URL (optional)")
    description = forms.CharField(widget=forms.widgets.Textarea,
                                  required=False,
                                  label="Video Description (optional)")

    class Meta(SecondStepSubmitVideoForm.Meta):
        fields = SecondStepSubmitVideoForm.Meta.fields + ['name',
                                                          'description']

    def clean_description(self):
        return sanitize(self.cleaned_data['description'],
                                 extra_filters=['img'])

    def save(self, **kwargs):
        commit = kwargs.get('commit', True)
        kwargs['commit'] = False
        video = SecondStepSubmitVideoForm.save(self, **kwargs)
        old_m2m = self.save_m2m
        def save_m2m():
            if self.cleaned_data['thumbnail_file']:
                self.instance.thumbnail_url = ''
                self.instance.save_thumbnail_from_file(
                    self.cleaned_data['thumbnail_file'])
            elif self.cleaned_data['thumbnail']:
                self.instance.thumbnail_url = self.data['thumbnail']
                self.instance.save_thumbnail_from_file(
                    self.cleaned_data['thumbnail'])
            old_m2m()
        if commit:
            video.save()
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return video

class ScrapedSubmitVideoForm(SecondStepSubmitVideoForm):
    def __init__(self, *args, **kwargs):
        self.scraped_data = kwargs.pop('scraped_data', {})
        if self.scraped_data.get('tags'):
            kwargs.setdefault('initial', {})['tags'] = \
                get_or_create_tags(self.scraped_data['tags'])
        SecondStepSubmitVideoForm.__init__(self, *args, **kwargs)

    def save(self, **kwargs):
        scraped_data = self.scraped_data
        if scraped_data.get('file_url_is_flaky'):
            file_url = None
        else:
            file_url = scraped_data.get('file_url', '')

        self.instance.name=scraped_data.get('title') or ''
        self.instance.site=self.sitelocation.site
        self.instance.status=models.VIDEO_STATUS_UNAPPROVED
        self.instance.description=sanitize(scraped_data.get('description') or \
                                               '',
                                           extra_filters=['img'])
        self.instance.file_url=file_url or ''
        self.instance.embed_code=scraped_data.get('embed') or ''
        self.instance.flash_enclosure_url=scraped_data.get(
            'flash_enclosure_url') or ''
        self.instance.website_url=self.cleaned_data['url']
        self.instance.thumbnail_url=scraped_data.get('thumbnail_url') or ''
        self.instance.when_published=scraped_data.get('publish_date')
        self.instance.video_service_user=scraped_data.get('user') or ''
        self.instance.video_service_url=scraped_data.get('user_url') or ''

        if file_url:
            self.instance.try_to_get_file_url_data()

        if self.instance.embed_code and not scraped_data.get('is_embedable',
                                                             True):
            self.instance.embed_code = '<span class="embed-warning">\
Warning: Embedding disabled by request.</span>' + self.instance.embed_code

        commit = kwargs.get('commit', True)
        kwargs['commit'] = False
        video = SecondStepSubmitVideoForm.save(self, **kwargs)

        old_m2m = self.save_m2m
        def save_m2m():
            video = self.instance
            if scraped_data.get('user'):
                author, created = User.objects.get_or_create(
                    username=scraped_data.get('user'),
                    defaults={'first_name': scraped_data.get('user')})
                if created:
                    author.set_unusable_password()
                    author.save()
                    get_profile_model().objects.create(
                        user=author,
                        website=scraped_data.get('user_url'))
                video.authors.add(author)
            old_m2m()

        if commit:
            video.save()
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return video


class EmbedSubmitVideoForm(NeedsDataSubmitVideoForm):
    embed = forms.CharField(widget=forms.Textarea,
                            label="Video <embed> code")

    class Meta(NeedsDataSubmitVideoForm.Meta):
        fields = NeedsDataSubmitVideoForm.Meta.fields + ['embed']

    def save(self, **kwargs):
        self.instance.website_url = self.cleaned_data['url']
        self.instance.embed_code = self.cleaned_data['embed']
        return NeedsDataSubmitVideoForm.save(self, **kwargs)

class DirectSubmitVideoForm(NeedsDataSubmitVideoForm):
    website_url = forms.URLField(required=False,
                                 label="Original Video Page URL (optional)")

    class Meta(NeedsDataSubmitVideoForm.Meta):
        fields = NeedsDataSubmitVideoForm.Meta.fields + ['website_url']

    def save(self, **kwargs):
        self.instance.file_url = self.cleaned_data['url']
        self.instance.try_to_get_file_url_data()
        return NeedsDataSubmitVideoForm.save(self, **kwargs)
