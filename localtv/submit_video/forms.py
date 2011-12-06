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
import importlib

from django import forms
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.conf import settings

from tagging.forms import TagField

from localtv import models
from localtv.utils import (quote_unicode_url, get_profile_model,
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

def get_extended_init_callable_for_class_name(class_name):
    # This is a hacky implementation of plugins.
    #
    # If the settings.LOCALTV_SUBMISSION_EXTRA_INIT option is defined,
    # then we look for a key equal to class_name.
    #
    # If that exists, we try calling importing that string and treating it as
    # a Python name to import, probably a callable. We return it!
    #
    # This helps us permit sites to have site-specific behavior on top of what
    # the SubmitVideoForm and friends do, without directly modifying this file.
    if getattr(settings, 'LOCALTV_SUBMISSION_EXTRA_INIT', None):
        if class_name in settings.LOCALTV_SUBMISSION_EXTRA_INIT:
            name_of_thing_to_call = settings.LOCALTV_SUBMISSION_EXTRA_INIT[
                class_name]
            module_name, entry = name_of_thing_to_call.rsplit('.', 1)
            module = importlib.import_module(module_name)
            return getattr(module, entry)

    # Otherwise, return a silly function that does nothing.
    silly_function = lambda *args, **kwargs: None
    return silly_function

class SubmitVideoForm(forms.Form):
    url = forms.URLField(verify_exists=True)

    def __init__(self, *args, **kwargs):
        # By convention, when you call this form's constructor, you
        # pass a keyword argument called construction_hint.
        #
        # This form can be constructed without it, so it's optional.
        #
        # We pass the construction_hint information through to the
        # "extra_init" system (which is a hacky form of plugins; see
        # get_extended_init_callable_for_class_name above) so that the "plugin"
        # can possibly alter the fields in the SubmitVideoForm.
        #
        # This is important so that the the form can be initialized differently
        # based on subtle differences in the request.GET. It's kind of hackish,
        # I realize.

        # First, we copy the data out and remove the keyword argument to avoid
        # scaring the superclass constructor:
        if 'construction_hint' in kwargs:
            construction_hint = kwargs['construction_hint']
            del kwargs['construction_hint']
        else:
            construction_hint = None

        super(SubmitVideoForm, self).__init__(*args, **kwargs)

        # Okay, now put the construction_hint back on.
        kwargs['construction_hint'] = construction_hint
        kwargs['self'] = self
        get_extended_init_callable_for_class_name('SubmitVideoForm')(
            *args,
             **kwargs)


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
        self.instance.status = models.Video.UNAPPROVED
        kwargs['self'] = self
        get_extended_init_callable_for_class_name('SecondStepSubmitVideoForm')(*args, **kwargs)

    def save(self, **kwargs):
        commit = kwargs.get('commit', True)
        kwargs['commit'] = False
        video = forms.ModelForm.save(self, **kwargs)
        if self.user.is_authenticated():
            video.user = self.user
        if self.sitelocation.user_is_admin(self.user):
            if (not self.sitelocation.enforce_tiers() or
                self.sitelocation.get_tier().remaining_videos() >= 1):
                video.status = models.Video.ACTIVE
        old_m2m = self.save_m2m
        def save_m2m():
            video = self.instance
            if video.is_active():
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
        self.vidscraper_video = kwargs.pop('vidscraper_video', {})
        if self.vidscraper_video.tags:
            kwargs.setdefault('initial', {})['tags'] = \
                get_or_create_tags(self.vidscraper_video.tags)
        SecondStepSubmitVideoForm.__init__(self, *args, **kwargs)

    def save(self, **kwargs):
        vidscraper_video = self.vidscraper_video
        instance = self.instance
        if vidscraper_video.file_url_is_flaky:
            file_url = None
        else:
            file_url = vidscraper_video.file_url

        instance.name=vidscraper_video.title or ''
        instance.site=self.sitelocation.site
        instance.status=models.Video.UNAPPROVED
        instance.description=sanitize(vidscraper_video.description or \
                                               '',
                                           extra_filters=['img'])
        instance.file_url=file_url or ''
        instance.embed_code=vidscraper_video.embed_code or ''
        instance.flash_enclosure_url=vidscraper_video.flash_enclosure_url or ''
        instance.website_url=vidscraper_video.link
        instance.thumbnail_url=vidscraper_video.thumbnail_url or ''
        instance.when_published=vidscraper_video.publish_datetime
        instance.video_service_user=vidscraper_video.user or ''
        instance.video_service_url=vidscraper_video.user_url or ''

        if file_url:
            instance.try_to_get_file_url_data()

        # XXX re-implement this
        #if instance.embed_code and not vidscraper_video.is_embedable:
        #    instance.embed_code = '<span class="embed-warning">\
        #Warning: Embedding disabled by request.</span>' + instance.embed_code

        commit = kwargs.get('commit', True)
        kwargs['commit'] = False
        video = SecondStepSubmitVideoForm.save(self, **kwargs)

        old_m2m = self.save_m2m
        def save_m2m():
            video = instance
            if vidscraper_video.user:
                author, created = User.objects.get_or_create(
                    username=vidscraper_video.user,
                    defaults={'first_name': vidscraper_video.user})
                if created:
                    author.set_unusable_password()
                    author.save()
                    get_profile_model().objects.create(
                        user=author,
                        website=vidscraper_video.user_url)
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
