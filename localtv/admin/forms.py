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

import re
import os.path
import feedparser

from django import forms
from django.forms.formsets import BaseFormSet
from django.forms.models import modelformset_factory, BaseModelFormSet
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import resolve
from django.http import Http404
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from tagging.forms import TagField

from localtv import models
from localtv import util

Profile = util.get_profile_model()

class EditVideoForm(forms.ModelForm):
    """
    """
    thumbnail = forms.ImageField(required=False)
    class Meta:
        model = models.Video
        fields = ('thumbnail', 'thumbnail_url', )

    def save(self, *args, **kwargs):
        if 'thumbnail' in self.cleaned_data:
            thumbnail = self.cleaned_data.pop('thumbnail')
            if thumbnail:
                self.instance.thumbnail_url = ''
                del self.cleaned_data['thumbnail_url']
                # since we're no longer using
                # that URL for a thumbnail
                self.instance.save_thumbnail_from_file(thumbnail)
        if 'thumbnail_url' in self.cleaned_data:
            thumbnail_url = self.cleaned_data.pop('thumbnail_url')
            if thumbnail_url and thumbnail_url != self.instance.thumbnail_url:
                self.instance.thumbnail_url = thumbnail_url
                self.instance.save_thumbnail()
        return forms.ModelForm.save(self, *args, **kwargs)

class BulkChecklistField(forms.ModelMultipleChoiceField):
    widget = forms.CheckboxSelectMultiple

    def label_from_instance(self, instance):
        if isinstance(instance, User):
            if instance.first_name:
                name = '%s %s' % (instance.first_name,
                                  instance.last_name)
            else:
                name = instance.username
        else:
            name = instance.name
        return mark_safe(u'<span>%s</span>' % (
                conditional_escape(name)))

class BooleanRadioField(forms.BooleanField):
    widget = forms.RadioSelect
    choices = (
        (True, 'On'),
        (False, 'Off'))

    def __init__(self, *args, **kwargs):
        forms.BooleanField.__init__(self, *args, **kwargs)
        self.widget.choices = self.choices

class SourceWidget(forms.HiddenInput):
    def render(self, name, value, attrs=None):
        if value is not None and not isinstance(value, basestring):
            value = '%s-%i' % (
                value.__class__.__name__.lower(),
                value.pk)
        return forms.HiddenInput.render(self, name, value)

class SourceChoiceField(forms.ModelChoiceField):
    widget = SourceWidget
    name = 'id'

    def __init__(self, *args, **kwargs):
        forms.ModelChoiceField.__init__(self, models.Source.objects, *args,
                                        **kwargs)

    def clean(self, value):
        forms.Field.clean(self, value)
        if value in ['', None]:
            return None
        model_name, pk = value.split('-')
        if model_name == 'feed':
            model = models.Feed
        elif model_name == 'savedsearch':
            model = models.SavedSearch
        else:
            raise forms.ValidationError(
                self.error_messages['invalid_choice'])
        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            raise forms.ValidationError(
                self.error_messages['invalid_choice'])


class SourceForm(forms.ModelForm):
    auto_categories = BulkChecklistField(required=False,
                                    queryset=models.Category.objects)
    auto_authors = BulkChecklistField(required=False,
                                 queryset=User.objects.order_by('username'))
    auto_approve = BooleanRadioField(required=False)
    thumbnail = forms.ImageField(required=False)
    delete_thumbnail = forms.BooleanField(required=False)

    class Meta:
        model = models.Source
        fields = ('auto_approve', 'auto_categories', 'auto_authors',
                  'thumbnail', 'delete_thumbnail')

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        if 'auto_approve' in self.initial:
            self.initial['auto_approve'] = bool(self.initial['auto_approve'])
        site = Site.objects.get_current()
        self.fields['auto_categories'].queryset = \
            self.fields['auto_categories'].queryset.filter(
            site=site)
        self.fields['auto_authors'].queryset = \
            self.fields['auto_authors'].queryset.order_by('username')

        if self.instance.pk is not None:
            if isinstance(self.instance, models.Feed):
                extra_fields = {
                    'name': forms.CharField(required=True,
                                            initial=self.instance.name),
                    'feed_url': forms.URLField(required=True,
                                               initial=self.instance.feed_url),
                    'webpage': forms.URLField(
                        required=False,
                        initial=self.instance.webpage)
                    }
                self._extra_field_names = ['name', 'feed_url', 'webpage']
            elif isinstance(self.instance, models.SavedSearch):
                extra_fields = {
                    'query_string' : forms.CharField(
                        required=True,
                        initial=self.instance.query_string)
                    }
                self._extra_field_names = ['query_string']
            self.fields.update(extra_fields)
            self._meta.fields = self._meta.fields + tuple(extra_fields.keys())

    def save(self, *args):
        if self.cleaned_data['thumbnail']:
            self.instance.save_thumbnail_from_file(
                self.cleaned_data['thumbnail'])
        if self.cleaned_data['delete_thumbnail']:
            self.instance.delete_thumbnails()
        return forms.ModelForm.save(self, *args)


    def _extra_fields(self):
        fields = [self[name] for name in self._extra_field_names]
        return fields
    extra_fields = property(_extra_fields)


class BaseSourceFormSet(BaseModelFormSet):

    def _construct_form(self, i, **kwargs):
        # Since we're doing something weird with the id field, we just use the
        # instance that's passed in when we create the formset
        if i < self.initial_form_count() and not kwargs.get('instance'):
            kwargs['instance'] = self.get_queryset()[i]
        return super(BaseModelFormSet, self)._construct_form(i, **kwargs)

    def add_fields(self, form, index):
        # We're adding the id field, so we can just call the
        # BaseFormSet.add_fields
        if index < self.initial_form_count():
            initial = self.queryset[index]
        else:
            initial = None
        self._pk_field = form.fields['id'] = SourceChoiceField(required=False,
                                              initial=initial)
        if initial:
            form.fields['BULK'] = forms.BooleanField(required=False)
        BaseFormSet.add_fields(self, form, index)


SourceFormset = modelformset_factory(models.Source,
                                     form=SourceForm,
                                     formset=BaseSourceFormSet,
                                     can_delete=True,
                                     extra=1)


class BulkEditVideoForm(EditVideoForm):
    BULK = forms.BooleanField(required=False)
    name = forms.CharField(
        required=False)
    file_url = forms.CharField(widget=forms.TextInput(
            attrs={'class': 'large_field'}),
                               required=False)
    embed_code = forms.CharField(widget=forms.Textarea,
                                 required=False)
    thumbnail_url = forms.CharField(widget=forms.TextInput(
            attrs={'class': 'large_field'}),
                                    required=False)
    tags = TagField(required=False,
                    widget=forms.Textarea)
    categories = BulkChecklistField(models.Category.objects, required=False)
    authors = BulkChecklistField(User.objects, required=False)
    when_published = forms.DateTimeField(required=False,
                                         widget=forms.DateTimeInput(
            attrs={'class': 'large_field'}))

    class Meta:
        model = models.Video
        fields = ('name', 'description', 'thumbnail', 'thumbnail_url', 'tags',
                  'categories', 'authors', 'when_published', 'file_url',
                  'embed_code')

    def __init__(self, *args, **kwargs):
        EditVideoForm.__init__(self, *args, **kwargs)
        site = Site.objects.get_current()
        self.fields['categories'].queryset = \
            self.fields['categories'].queryset.filter(
            site=site)
        self.fields['authors'].queryset = \
            self.fields['authors'].queryset.order_by('username')

    def clean_name(self):
        if self.instance.pk and not self.cleaned_data.get('name'):
            raise forms.ValidationError('This field is required.')
        return self.cleaned_data['name']

VideoFormSet = modelformset_factory(models.Video,
                                    form=BulkEditVideoForm,
                                    can_delete=True,
                                    extra=1)


class EditSettingsForm(forms.ModelForm):
    """
    """
    title = forms.CharField(label="Site Title", max_length=50)
    tagline = forms.CharField(label="Site Tagline", required=False,
                              max_length=250)
    about_html = forms.CharField(label="About Us Page (use html)",
                                 widget=forms.Textarea, required=False)
    sidebar_html = forms.CharField(label="Sidebar Blurb (use html)",
                                   widget=forms.Textarea, required=False)
    footer_html = forms.CharField(label="Footer Blurb (use html)",
                                  widget=forms.Textarea, required=False,
                                  help_text="In addition to any footer text "
                                  "you would like to add, we suggest using "
                                  "this space to paste in a Google Analytics "
                                  "tracking code, which will provide "
                                  "excellent statistics on usage of your "
                                  "site.")
    logo = forms.ImageField(label="Logo Image", required=False)
    background = forms.ImageField(label="Background Image", required=False)
    display_submit_button = forms.BooleanField(
        label="Display the 'submit a video' nav item",
        required=False)
    submission_requires_login = forms.BooleanField(
        label="Require users to login to submit a video",
        required=False)
    css = forms.CharField(
        label="Custom CSS",
        help_text="Here you can append your own CSS to customize your site.",
        widget=forms.Textarea, required=False)
    use_original_date = forms.BooleanField(
        label="Use Original Date?",
        help_text="If set, use the original date the video was posted.  "
        "Otherwise, use the date the video was added to this site.",
        required=False)

    class Meta:
        model = models.SiteLocation
        exclude = ['site', 'status', 'admins']


    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        if self.instance:
            self.initial['title'] = self.instance.site.name

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if not logo:
            return logo
        if len(logo.name) > 60:
            name, ext = os.path.splitext(logo.name)
            logo.name = name[:60] + ext
        return logo

    def clean_background(self):
        background = self.cleaned_data.get('background')
        if not background:
            return background
        if len(background.name) > 60:
            name, ext = os.path.splitext(background.name)
            background.name = name[:60] + ext
        return background

    def save(self):
        sl = forms.ModelForm.save(self)
        sl.site.name = self.cleaned_data['title']
        sl.site.save()
        models.SiteLocation.objects.clear_cache()
        return sl

class CategoryForm(forms.ModelForm):
    class Meta:
        model = models.Category
        exclude = ['site']

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)

        self.site = Site.objects.get_current()
        self.fields['parent'].queryset = models.Category.objects.filter(
            site=self.site)

    def clean(self):
        self.fields['site'] = forms.ModelChoiceField(Site.objects)
        self.cleaned_data['site'] = self.site
        try:
            return forms.ModelForm.clean(self)
        finally:
            del self.fields['site']
            del self.cleaned_data['site']

    def unique_error_message(self, unique_check):
        return 'Category with this %s already exists.' % (
            unique_check[0],)

class BaseCategoryFormSet(BaseModelFormSet):

    def clean(self):
        BaseModelFormSet.clean(self)
        deleted_ids = set()
        parents = {}
        # first pass: get the deleted items and map parents to items
        for i, data in enumerate(self.cleaned_data):
            if data.get('DELETE'):
                deleted_ids.add(data['id'])
            if data.get('parent'):
                parents.setdefault(data['parent'], set()).add(i)

        # second pass: set children of deleted items to None:
        for parent in deleted_ids:
            if parent not in parents:
                continue
            for form_index in parents[parent]:
                form = self.forms[form_index]
                form.instance.parent = None
                form.instance.save()

    def add_fields(self, form, i):
        BaseModelFormSet.add_fields(self, form, i)
        if i < self.initial_form_count():
            form.fields['BULK'] = forms.BooleanField(required=False)


CategoryFormSet = modelformset_factory(models.Category,
                                       form=CategoryForm,
                                       formset=BaseCategoryFormSet,
                                       can_delete=True,
                                       extra=0)

class FlatPageForm(forms.ModelForm):
    url = forms.CharField(required=True,
                          label='URL',
                          max_length=100,
                          help_text=("The URL for the page.  It must start "
                                     "with a '/' character."))
    content = forms.CharField(required=True,
                              label='Content',
                              widget=forms.Textarea,
                              help_text=("This is everything you want to "
                                         "appear on the page.  The header and "
                                         "footer of your site will be "
                                         "automatically included.  This can "
                                         "contain HTML."))
    class Meta:
        model = FlatPage
        fields = ['url', 'title', 'content']

    def clean_url(self):
        value = self.cleaned_data['url']
        if not value.startswith('/'):
            raise forms.ValidationError("URL must start with a '/' character")
        if getattr(settings, 'APPEND_SLASH', False) and \
                not value.endswith('/'):
            # append the trailing slash
            value = value + '/'
        existing = FlatPage.objects.filter(
            url = value,
            sites=Site.objects.get_current())
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.count():
            raise forms.ValidationError(
                'Flatpage with that URL already exists.')
        try:
            resolve(value)
        except Http404:
            pass # good, the URL didn't resolve
        else:
            raise forms.ValidationError(
                'View with that URL already exists.')
        return value

class BaseFlatPageFormSet(BaseModelFormSet):

    def add_fields(self, form, i):
        BaseModelFormSet.add_fields(self, form, i)
        if i < self.initial_form_count():
            form.fields['BULK'] = forms.BooleanField(required=False)

FlatPageFormSet = modelformset_factory(FlatPage,
                                       form=FlatPageForm,
                                       formset=BaseFlatPageFormSet,
                                       can_delete=True,
                                       extra=0)
class AuthorForm(forms.ModelForm):
    role = forms.ChoiceField(choices=(
            ('user', 'User'),
            ('admin', 'Admin')),
                             required=False)
    logo = forms.ImageField(required=False,
                            label='Photo')
    description = forms.CharField(
        widget=forms.Textarea,
        required=False)
    website = forms.URLField(required=False)
    password_f = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label='Password',
        help_text=('If you do not specify a password, the user will not be '
                   'allowed to log in.'))
    password_f2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        label='Confirm Password')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role',
                  'logo', 'description', 'password_f', 'password_f2']

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        site = Site.objects.get_current()
        self.sitelocation = models.SiteLocation.objects.get(site=site)
        if self.instance.pk:
            if self.sitelocation.user_is_admin(self.instance):
                self.fields['role'].initial = 'admin'
            else:
                self.fields['role'].initial = 'user'
            try:
                profile = self.instance.get_profile()
            except Profile.DoesNotExist:
                profile = Profile.objects.create(
                    user=self.instance)
            self.fields['description'].initial = profile.description
            self.fields['website'].initial = profile.website

    def clean_username(self):
        value = self.cleaned_data.get('username')
        if not self.instance.pk and \
                User.objects.filter(username=value).count():
            raise forms.ValidationError('That username already exists.')
        return value

    def clean(self):
        if self.instance.is_superuser and 'DELETE' in self.cleaned_data:
            # can't delete a superuser, so remove that from the cleaned data
            self.cleaned_data['DELETE'] = False
            prefix = self.add_prefix('DELETE')
            self.data[prefix] = '' # have to set our data directly because
                                   # BaseModelFormSet pulls the value from
                                   # there
        if 'password_f' in self.cleaned_data or \
                'password_f2' in self.cleaned_data:
            password = self.cleaned_data.get('password_f')
            password2 = self.cleaned_data.get('password_f2')
            if password != password2:
                del self.cleaned_data['password_f']
                del self.cleaned_data['password_f2']
                raise forms.ValidationError(
                    'The passwords do not match.')
        return self.cleaned_data

    def save(self, **kwargs):
        is_new = not self.instance.pk
        author = forms.ModelForm.save(self, **kwargs)
        if self.cleaned_data.get('password_f'):
            author.set_password(self.cleaned_data['password_f'])
        elif is_new:
            author.set_unusable_password()
        author.save()
        if 'logo' in self.cleaned_data or 'description' in self.cleaned_data \
                or 'website' in self.cleaned_data:
            try:
                profile = author.get_profile()
            except Profile.DoesNotExist:
                profile = Profile.objects.create(
                    user=author)
            if self.cleaned_data.get('logo'):
                logo = self.cleaned_data['logo']
                profile.logo = logo
            if 'description' in self.cleaned_data:
                profile.description = self.cleaned_data['description']
            if 'website' in self.cleaned_data:
                profile.website = self.cleaned_data['website']
            profile.save()
        if self.cleaned_data.get('role'):
            if self.cleaned_data['role'] == 'admin':
                if not author.is_superuser:
                    self.sitelocation.admins.add(author)
            else:
                self.sitelocation.admins.remove(author)
            self.sitelocation.save()
        return author

AuthorFormSet = modelformset_factory(User,
                                     form=AuthorForm,
                                     can_delete=True,
                                     extra=0)



class AddFeedForm(forms.Form):
    SERVICE_PROFILES = (
        (re.compile(
                r'^(http://)?(www\.)?youtube\.com/profile(_videos)?'
                r'\?(\w+=\w+&)*user=(?P<name>\w+)'),
         'youtube'),
        (re.compile(r'^(http://)?(www\.)?youtube\.com/((rss/)?user/)?'
                    r'(?P<name>\w+)'),
         'youtube'),
        (re.compile(r'^(http://)?(www\.)?(?P<name>\w+)\.blip\.tv'), 'blip'),
        (re.compile(
                r'^(http://)?(www\.)?vimeo\.com/(?P<name>(channels/)?\w+)$'),
         'vimeo'),
        (re.compile(
                r'^(http://)?(www\.)?dailymotion\.com/(\w+/)*(?P<name>\w+)/1'),
         'dailymotion'),
        )

    SERVICE_FEEDS = {
        'youtube': ('http://gdata.youtube.com/feeds/base/users/%s/'
                    'uploads?alt=rss&v=2&orderby=published'),
        'blip': 'http://%s.blip.tv/rss',
        'vimeo': 'http://www.vimeo.com/%s/videos/rss',
        'dailymotion': 'http://www.dailymotion.com/rss/%s/1',
        }

    feed_url = forms.URLField(required=True,
                              widget=forms.TextInput(
            attrs={'class': 'livesearch_feed_url'}))

    @staticmethod
    def _feed_url_key(feed_url):
        return 'localtv:add_feed_form:%i' % hash(feed_url)

    def clean_feed_url(self):
        value = self.cleaned_data['feed_url']
        for regexp, service in self.SERVICE_PROFILES:
            match = regexp.match(value)
            if match:
                username = match.group('name')
                value = self.SERVICE_FEEDS[service] % username
                break

        site = Site.objects.get_current()
        if models.Feed.objects.filter(feed_url=value,
                                      site=site):
            raise forms.ValidationError(
                'That feed already exists on this site.')

        key = self._feed_url_key(value)
        parsed = cache.get(key)
        if parsed is None:
            parsed = feedparser.parse(value)
            if 'bozo_exception' in parsed:
                # can't cache exceptions
                del parsed['bozo_exception']
            cache.set(key, parsed)
        if not parsed.feed or not (parsed.entries or
                                   parsed.feed.get('title')):
            raise forms.ValidationError('It does not appear that %s is an '
                                        'RSS/Atom feed URL.' % value)

        # drop the parsed data into cleaned_data so that other code can re-use
        # the data
        self.cleaned_data['parsed_feed'] = parsed

        return value
