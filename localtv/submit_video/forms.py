# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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

import urlparse

from django import forms
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.conf import settings
from django.db.models import Q
from tagging.forms import TagField
import vidscraper
from vidscraper.errors import CantIdentifyUrl

from localtv.exceptions import CannotOpenImageUrl
from localtv.models import Video, SiteLocation
from localtv.templatetags.filters import sanitize


class SubmitURLForm(forms.Form):
    """Accepts submission of a URL."""
    url = forms.URLField(verify_exists=False)

    def _validate_unique(self, url=None, guid=None):
        identifiers = Q()
        if url is not None:
            identifiers |= Q(website_url=url) | Q(file_url=url)
        if guid is not None:
            identifiers |= Q(guid=guid)
        videos = Video.objects.filter(identifiers,
                                      ~Q(status=Video.REJECTED),
                                      site=Site.objects.get_current())

        # HACK: We set attributes on the form so that we can provide
        # backwards-compatible template context. We should remove this when it's
        # no longer needed.
        try:
            video = videos[0]
        except IndexError:
            self.was_duplicate = False
            self.duplicate_video = None
            self.duplicate_video_pk = None
        else:
            self.was_duplicate = True
            self.duplicate_video_pk = video.pk
            if video.status == Video.ACTIVE:
                self.duplicate_video = video
            else:
                self.duplicate_video = None
            raise ValidationError("That video has already been submitted!")

    def clean_url(self):
        url = urlparse.urldefrag(self.cleaned_data['url'])[0]
        self._validate_unique(url=url)
        self.video_cache = None
        try:
            self.video_cache = vidscraper.auto_scrape(url, api_keys={
                'vimeo_key': getattr(settings, 'VIMEO_API_KEY', None),
                'vimeo_secret': getattr(settings, 'VIMEO_API_SECRET', None),
                'ustream_key': getattr(settings, 'USTREAM_API_KEY', None)
            })
        except CantIdentifyUrl:
            pass
        else:
            if self.video_cache.link is not None and url != self.video_cache.link:
                url = self.video_cache.link
                self._validate_unique(url=url, guid=self.video_cache.guid)
            elif self.video_cache.guid is not None:
                self._validate_unique(guid=self.video_cache.guid)
        return url


class SubmitVideoForm(forms.ModelForm):
    tags = TagField(required=False, label="Tags (optional)",
                    help_text=("You can also <span class='url'>optionally add "
                               "tags</span> for the video (below)."))

    if getattr(settings, 'LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL', False):
        contact = Video._meta.get_field('contact').formfield(
                              label='E-mail (required)',
                              required=True)

    thumbnail_file = forms.ImageField(required=False,
                                      label="Thumbnail File (optional)")

    def __init__(self, request, url, *args, **kwargs):
        self.request = request
        super(SubmitVideoForm, self).__init__(*args, **kwargs)
        if request.user.is_authenticated():
            self.initial['contact'] = request.user.email
            self.instance.user = request.user
        self.instance.site = Site.objects.get_current()
        self.instance.status = Video.UNAPPROVED
        if 'website_url' in self.fields:
            self.instance.file_url = url
        elif not self.instance.website_url:
            self.instance.website_url = url

    def _post_clean(self):
        super(SubmitVideoForm, self)._post_clean()
        # By this time, cleaned data has been applied to the instance.
        identifiers = Q()
        if self.instance.website_url:
            identifiers |= Q(website_url=self.instance.website_url)
        if self.instance.file_url:
            identifiers |= Q(file_url=self.instance.file_url)
        if self.instance.guid:
            identifiers |= Q(guid=self.instance.guid)

        videos = Video.objects.filter(identifiers,
                                      ~Q(status=Video.REJECTED),
                                      site=Site.objects.get_current())
        if videos.exists():
            self._update_errors({NON_FIELD_ERRORS: ["That video has already "
                                                    "been submitted!"]})

    def clean_description(self):
        return sanitize(self.cleaned_data['description'],
                                 extra_filters=['img'])

    def save(self, commit=True):
        instance = super(SubmitVideoForm, self).save(commit=False)

        if self.request.user_is_admin():
            sitelocation = SiteLocation.objects.get_current()
            if (not sitelocation.enforce_tiers() or
                sitelocation.get_tier().remaining_videos() >= 1):
                instance.status = Video.ACTIVE

        if 'website_url' in self.fields:
            # Then this was a form which required a website_url - i.e. a direct
            # file submission. TODO: Find a better way to mark this?
            instance.try_to_get_file_url_data()

        old_m2m = self.save_m2m
        def save_m2m():
            if instance.status == Video.ACTIVE:
                # when_submitted isn't set until after the save
                instance.when_approved = instance.when_submitted
                instance.save()
            if hasattr(instance, 'save_m2m'):
                # Then it was generated with from_vidscraper_video
                instance.save_m2m()
            
            if self.cleaned_data.get('thumbnail_file', None):
                instance.thumbnail_url = ''
                instance.save_thumbnail_from_file(
                    self.cleaned_data['thumbnail_file'])

            # TODO: Should be delayed as a task
            if instance.thumbnail_url and not instance.has_thumbnail:
                try:
                    instance.save_thumbnail()
                except CannotOpenImageUrl:
                    pass # we'll get it later
            if self.cleaned_data.get('tags'):
                instance.tags = self.cleaned_data['tags']
            old_m2m()
        if commit:
            instance.save()
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return instance
