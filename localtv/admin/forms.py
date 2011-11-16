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

import datetime
import re
import os.path
import feedparser
import urlparse

import django.template.defaultfilters
from django import forms
from django.forms.formsets import BaseFormSet
from django.forms.models import modelformset_factory, BaseModelFormSet, \
    construct_instance
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.urlresolvers import resolve
from django.http import Http404
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from tagging.forms import TagField
from tagging.utils import edit_string_for_tags

import localtv.settings
from localtv import models
from localtv import utils
import localtv.tiers

from vidscraper.errors import CantIdentifyUrl
from vidscraper import auto_feed


class BulkFormSetMixin(object):
    """
    Mixin form-like which adds a bulk field to each form.
    """
    def add_fields(self, form, i):
        super(BulkFormSetMixin, self).add_fields(form, i)
        if i < self.initial_form_count():
            form.fields['BULK'] = forms.BooleanField(required=False)

    @property
    def bulk_forms(self):
        for form in self.initial_forms:
            if form.cleaned_data and form.cleaned_data['BULK'] and \
                    not self._should_delete_form(form):
                yield form

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
                value._meta.module_name,
                value.pk)
        return forms.HiddenInput.render(self, name, value)

class SourceChoiceField(forms.TypedChoiceField):
    widget = SourceWidget
    name = 'id'

    def __init__(self, **kwargs):
        feed_choices = [('feed-%s' % feed.pk, feed) for feed in
                         models.Feed.objects.all()]
        search_choices = [('savedsearch-%s' % search.pk, search) for search in
                          models.SavedSearch.objects.all()]
        choices = feed_choices + search_choices
        initial = kwargs.pop('initial', None)
        if initial:
            initial = '%s-%s' % (initial._meta.module_name, initial.pk)
        else:
            initial = None
        forms.TypedChoiceField.__init__(self,
                                        choices=choices,
                                        coerce=self.coerce,
                                        empty_value=None,
                                        initial=initial,
                                        **kwargs)
    def coerce(self, value):
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
    avoid_frontpage = forms.BooleanField(required=False)

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
            self._meta.model = type(self.instance)

    def save(self, *args, **kwargs):
        if self.cleaned_data.get('thumbnail'):
            self.instance.save_thumbnail_from_file(
                self.cleaned_data['thumbnail'])
        if self.cleaned_data.get('delete_thumbnail'):
            self.instance.delete_thumbnails()

        # if the categories or authors changed, update unchanged videos to the
        # new values
        if self.instance.pk:
            old_categories = set(self.instance.auto_categories.all())
            old_authors = set(self.instance.auto_authors.all())
            source = forms.ModelForm.save(self, *args, **kwargs)
            new_categories = set(source.auto_categories.all())
            new_authors = set(source.auto_authors.all())
            if old_categories != new_categories or \
                    old_authors != new_authors:
                for v in source.video_set.all():
                    changed = False
                    if set(v.categories.all()) == old_categories:
                        changed = True
                        v.categories = new_categories
                    if set(v.authors.all()) == old_authors:
                        changed = True
                        v.authors = new_authors
                    if changed:
                        v.save()
            return source
        else:
            return forms.ModelForm.save(self, *args, **kwargs)

    def _extra_fields(self):
        fields = [self[name] for name in self._extra_field_names]
        return fields
    extra_fields = property(_extra_fields)


class BaseSourceFormSet(BulkFormSetMixin, BaseModelFormSet):

    def _construct_form(self, i, **kwargs):
        # Since we're doing something weird with the id field, we just use the
        # instance that's passed in when we create the formset
        if i < self.initial_form_count() and not kwargs.get('instance'):
            kwargs['instance'] = self.get_queryset()[i]
        return super(BaseModelFormSet, self)._construct_form(i, **kwargs)

    def save_new_objects(self, commit=True):
        """
        Editing this form does not result in new objects.
        """
        return []

    def save_existing_objects(self, commit=True):
        """
        Have to re-implement this, because our PK values aren't normal in this
        formset.
        """
        self.changed_objects = []
        self.deleted_objects = []
        if not self.get_queryset():
            return []

        bulk_action = self.data.get('bulk_action', '')

        saved_instances = []
        for form in self.initial_forms:
            pk_name = self._pk_field.name
            raw_pk_value = form._raw_value(pk_name)

            # clean() for different types of PK fields can sometimes return
            # the model instance, and sometimes the PK. Handle either.
            obj = form.fields[pk_name].clean(raw_pk_value)

            if self.can_delete:
                raw_delete_value = form._raw_value('DELETE')
                raw_bulk_value = form._raw_value('BULK')
                should_delete = form.fields['DELETE'].clean(raw_delete_value)
                bulk_delete = (bulk_action == 'remove') and \
                    form.fields['BULK'].clean(raw_bulk_value)
                if should_delete or bulk_delete:
                    self.deleted_objects.append(obj)
                    if self.data.get('keep'):
                        form.instance.video_set.all().update(
                            search=None, feed=None)
                    obj.delete()
                    continue
            if form.has_changed():
                self.changed_objects.append((obj, form.changed_data))
                saved_instances.append(self.save_existing(form, obj,
                                                          commit=commit))
                if not commit:
                    self.saved_forms.append(form)
        return saved_instances

    def clean(self):
        bulk_edits = self.extra_forms[0].cleaned_data
        for key in list(bulk_edits.keys()): # get the list because we'll be
                                            # changing the dictionary
            if bulk_edits[key] in ['', None] or key == 'id':
                del bulk_edits[key]
        if bulk_edits:
            for form in self.bulk_forms:
                for key, value in bulk_edits.items():
                    if key == 'auto_categories':
                        # categories append, not replace
                        form.cleaned_data[key] = (
                            list(form.cleaned_data[key]) +
                            list(value))
                    else:
                        form.cleaned_data[key] = value
                form.instance = construct_instance(form, form.instance,
                                                   form._meta.fields,
                                                   form._meta.exclude)
        return BaseModelFormSet.clean(self)

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


class WidgetSettingsForm(forms.ModelForm):

    class Meta:
        model = models.WidgetSettings
        exclude = ['site', 'has_thumbnail', 'thumbnail_extension']

    def save(self):
        ws = forms.ModelForm.save(self)
        if ws.icon:
            ws.icon.open()
            cf = ContentFile(ws.icon.read())
            ws.save_thumbnail_from_file(cf)
        return ws

class VideoAsUrlWidget(forms.TextInput):
    def render(self, name, value, attrs=None):
        if value and not isinstance(value, basestring):
            try:
                pk = getattr(value, 'pk')
            except AttributeError:
                pk = value
            instance = models.Video.objects.get(pk=pk)
            site = Site.objects.get_current()
            value = 'http://%s%s' % (
                site.domain, instance.get_absolute_url())
        return forms.TextInput.render(self, name, value, attrs)

class VideoAsUrlField(forms.CharField):
    widget = VideoAsUrlWidget

    def clean(self, value):
        if not value:
            return None
        parts = urlparse.urlsplit(value)
        site = Site.objects.get_current()
        if parts.netloc and parts.netloc != site.domain:
            raise forms.ValidationError('Video must be from this site')
        path = parts.path
        if not path.startswith('/'):
            path = '/' + path
        try:
            view, args, kwargs = resolve(path)
        except Http404:
            raise ValidationError('Not a valid URL')
        if 'video_id' in kwargs:
            try:
                return models.Video.objects.get(pk=kwargs['video_id'])
            except models.Video.DoesNotExist:
                pass
        raise ValidationError('Not a valid URL')

class DayTimeWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = (
            forms.Select(),
            forms.Select(),
            forms.Select())
        super(DayTimeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            time, am_pm = value.hour, 0
            if time == 0:
                time, am_pm = 12, 0
            elif time == 12:
                time, am_pm = 12, 12
            elif time > 12:
                time, am_pm = time - 12, 12
            return value.weekday(), time, am_pm
        return [None, None, None]

class DayTimeField(forms.MultiValueField):
    widget = DayTimeWidget

    def __init__(self, *args, **kwargs):
        fields = (
            forms.ChoiceField(choices=((6, 'Sunday'),
                                       (0, 'Monday'),
                                       (1, 'Tuesday'),
                                       (2, 'Wednesday'),
                                       (3, 'Thursday'),
                                       (4, 'Friday'),
                                       (5, 'Saturday'))),
            forms.ChoiceField(choices=((i, str(i)) for i in range(1, 13))),
            forms.ChoiceField(choices=((0, 'am'),
                                       (12, 'pm'))))
        super(DayTimeField, self).__init__(fields, *args, **kwargs)
        for widget, field in zip(self.widget.widgets, fields):
            widget.choices = field.choices

    def compress(self, data_list):
        if data_list:
            try:
                day, time, am_pm = (int(i) for i in data_list)
            except ValueError:
                raise ValidationError(self.error_messages['invalid'])
            if time == 12:
                if am_pm: # 12pm is noon
                    am_pm = 0
                else: # 12am is midnight
                    time = 0
            else:
                time = time + am_pm
            return datetime.datetime(1, 1, day + 1, time) # simple datetime
                                                          # represent the day
                                                          # of the week and the
                                                          # hour to send
        return None

class NewsletterSettingsForm(forms.ModelForm):
    intro = forms.CharField(max_length=200,
                            widget=forms.Textarea)
    video1 = VideoAsUrlField('Video 1', required=False,
                             help_text='A URL of a video on your site.')
    video2 = VideoAsUrlField('Video 2', required=False,
                             help_text='A URL of a video on your site.')
    video3 = VideoAsUrlField('Video 3', required=False,
                             help_text='A URL of a video on your site.')
    video4 = VideoAsUrlField('Video 4', required=False,
                             help_text='A URL of a video on your site.')
    video5 = VideoAsUrlField('Video 5', required=False,
                             help_text='A URL of a video on your site.')

    repeat = forms.ChoiceField(choices=((0, 'No'),
                                        (24 * 7, 'Yes, weekly'),
                                        (24 * 7 * 2, 'Yes, bi-weekly')),
                               label='Send Newsletter Automatically?',
                               help_text=('Select how often you would like '
                                          'the newsletter to send.'))
    last_sent = DayTimeField(label='Choose a date/time to send your newsletter')
    
    class Meta:
        model = models.NewsletterSettings
        exclude = ['sitelocation']

    def clean(self):
        if self.cleaned_data['repeat']:
            if not self.instance.last_sent:
                last_sent = datetime.datetime.now()
            else:
                last_sent = self.instance.last_sent
            week_start = last_sent - datetime.timedelta(
                days=last_sent.weekday(),
                hours=last_sent.hour,
                minutes=last_sent.minute,
                seconds=last_sent.second)
            # week_start is the start of the week that the email was last sent
            delta = datetime.timedelta(
                days=self.cleaned_data['last_sent'].weekday(),
                hours=self.cleaned_data['last_sent'].hour)
            last_sent = week_start + delta
            now = datetime.datetime.now()
            repeat = datetime.timedelta(hours=int(self.cleaned_data['repeat']))
            if last_sent > now:
                # we've picked a time in the future, so go back
                last_sent -= datetime.timedelta(days=7)
            if last_sent + repeat < now:
                # repeat would be in the past, so move forward
                last_sent += repeat
            self.cleaned_data['last_sent'] = last_sent
        return super(forms.ModelForm, self).clean()

    def save(self, commit=True):
        instance = super(forms.ModelForm, self).save(commit=False)
        if not instance.repeat:
            instance.last_sent = None
        if commit:
            instance.save()
            self.save_m2m()
        return instance


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

class BaseFlatPageFormSet(BulkFormSetMixin, BaseModelFormSet):
    pass

FlatPageFormSet = modelformset_factory(FlatPage,
                                       form=FlatPageForm,
                                       formset=BaseFlatPageFormSet,
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
        (re.compile(r'^(http://)?([^/]*)blip\.tv'), 'blip'),
        (re.compile(
                r'^(http://)?(www\.)?vimeo\.com/(?P<name>(channels/)?\w+)$'),
         'vimeo'),
        (re.compile(
                r'^(http://)?(www\.)?dailymotion\.com/(\w+/)*(?P<name>\w+)/1'),
         'dailymotion'),
        )

    def _blip_add_rss_skin(url):
        if '?' in url:
            return url + '&skin=rss'
        else:
            return url + '?skin=rss'

    SERVICE_FEEDS = {
        'youtube': ('http://gdata.youtube.com/feeds/base/users/%s/'
                    'uploads?alt=rss&v=2&orderby=published'),
        'blip': _blip_add_rss_skin,
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
        url = self.cleaned_data['feed_url']
        try:
            scraped_feed = auto_feed(url)
            url = scraped_feed.url
        except CantIdentifyUrl:
            raise forms.ValidationError('It does not appear that %s is an '
                                        'RSS/Atom feed URL.' % url)

        site = Site.objects.get_current()
        if models.Feed.objects.filter(feed_url=url,
                                      site=site):
            raise forms.ValidationError(
                'That feed already exists on this site.')

        self.cleaned_data['scraped_feed'] = scraped_feed

        return url
