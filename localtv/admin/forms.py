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

import datetime
import os.path
import urlparse

from django import forms
from django.forms.formsets import BaseFormSet, DELETION_FIELD_NAME
from django.forms.models import modelformset_factory, BaseModelFormSet, \
    construct_instance
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.urlresolvers import resolve
from django.db.models.fields.files import FileField, FieldFile
from django.http import Http404
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from haystack import connections

from tagging.forms import TagField

from localtv import models, utils
from localtv.settings import API_KEYS
from localtv.tasks import video_save_thumbnail, feed_update, CELERY_USING
from localtv.user_profile import forms as user_profile_forms

from vidscraper import auto_feed

Profile = utils.get_profile_model()

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
            if (hasattr(form, 'cleaned_data') and
                form.cleaned_data.get('BULK') and
                not self._should_delete_form(form)):
                yield form

class EditVideoForm(forms.ModelForm):
    """
    """
    thumbnail = forms.ImageField(required=False)
    class Meta:
        model = models.Video
        fields = ('thumbnail', 'thumbnail_url', )

    def save(self, commit=True):
        if 'thumbnail' in self.cleaned_data:
            thumbnail = self.cleaned_data.pop('thumbnail')
            if thumbnail:
                self.instance.thumbnail_url = ''
                del self.cleaned_data['thumbnail_url']
                # since we're no longer using
                # that URL for a thumbnail
                self.instance.save_thumbnail_from_file(thumbnail,
                                                       update=False)
        if 'thumbnail_url' in self.cleaned_data:
            thumbnail_url = self.cleaned_data.pop('thumbnail_url')
            if (thumbnail_url and not
                models.Video.objects.get(id=self.instance.id).thumbnail_url == thumbnail_url):
                self.instance.thumbnail_url = thumbnail_url
                video_save_thumbnail.delay(self.instance.pk,
                                           using=CELERY_USING)
        return forms.ModelForm.save(self, commit=commit)

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

    def __init__(self, feeds, searches, **kwargs):
        feed_choices = [('feed-%s' % feed.pk, feed) for feed in
                         feeds]
        search_choices = [('savedsearch-%s' % search.pk, search) for search in
                          searches]
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
                                    queryset=models.Category.objects.filter(
                                                site=settings.SITE_ID))
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
                self.cleaned_data['thumbnail'],
                update=False)
        if self.cleaned_data.get('delete_thumbnail'):
            self.instance.delete_thumbnail()

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
    @property
    def _qs_cache(self):
        """
        Returns a dictionary of related objects that can be shared for form
        fields among the forms in the set.

        """
        # We use SharedQuerySet so that the form fields don't make fresh
        # querysets when they generate their choices.
        if not hasattr(self, '_real_qs_cache'):
            self._real_qs_cache = {
                'categories': SourceForm.base_fields[
                                  'auto_categories'].queryset._clone(
                                      utils.SharedQuerySet),
                'authors': SourceForm.base_fields[
                                  'auto_authors'].queryset._clone(
                                      utils.SharedQuerySet),
                'feeds': utils.SharedQuerySet(models.Feed),
                'searches': utils.SharedQuerySet(models.SavedSearch),
            }
        return self._real_qs_cache

    def _construct_form(self, i, **kwargs):
        # Since we're doing something weird with the id field, we just use the
        # instance that's passed in when we create the formset
        # TODO: Stop doing something weird.
        if i < self.initial_form_count() and not kwargs.get('instance'):
            kwargs['instance'] = self.get_queryset()[i]
        form = super(BaseModelFormSet, self)._construct_form(i, **kwargs)
        form.fields['auto_categories'].queryset = self._qs_cache['categories']
        form.fields['auto_authors'].queryset = self._qs_cache['authors']
        return form

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
        self._pk_field = form.fields['id'] = SourceChoiceField(
                                          required=False,
                                          initial=initial,
                                          feeds=self._qs_cache['feeds'],
                                          searches=self._qs_cache['searches'])
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
    categories = BulkChecklistField(models.Category.objects.filter(
                                    site=settings.SITE_ID),
                                    required=False)
    authors = BulkChecklistField(User.objects.order_by('username'),
                                 required=False)
    skip_authors = forms.BooleanField(required=False,
                                      initial=True,
                                      widget=forms.HiddenInput)
    when_published = forms.DateTimeField(
        required=False,
        help_text='Format: yyyy-mm-dd hh:mm:ss',
        widget=forms.DateTimeInput(
            attrs={'class': 'large_field'}))

    class Meta:
        model = models.Video
        fields = ('name', 'description', 'thumbnail', 'thumbnail_url', 'tags',
                  'categories', 'authors', 'when_published', 'file_url',
                  'embed_code', 'skip_authors')

    def __init__(self, cache_for_form_optimization=None,  *args, **kwargs):
        # The cache_for_form_optimization is an object that is
        # optionally created by the request that calls
        # BulkEditForm. One difficulty with BulkEditForms is that the
        # forms generate similar data over and over again; we can
        # avoid some database hits by running some queries just once
        # (at BulkEditForm instantiation time), rather than once per
        # sub-form.
        #
        # However, it is unsafe to cache data in the BulkEditForm
        # class because that persists for as long as the Python
        # process does (meaning that subsequent requests will use the
        # same cache).
        EditVideoForm.__init__(self, *args, **kwargs)

        # We have to initialize tags manually because the model form
        # (django.forms.models.model_to_dict) only collects fields and
        # relations, and not descriptors like Video.tags
        self.initial['tags'] = utils.edit_string_for_tags(self.instance.tags)

    def _post_clean(self):
        if not self.instance.pk:
            # don't run the instance validation checks on the extra form field.
            # This also doesn't set the values on the instance, but since we
            # get the values directly from `cleaned_data` in bulk_edit_views.py
            # it doesn't matter.
            return
        return super(BulkEditVideoForm, self)._post_clean()

    def clean_name(self):
        if self.instance.pk and not self.cleaned_data.get('name'):
            raise forms.ValidationError('This field is required.')
        return self.cleaned_data['name']

    def clean_skip_authors(self):
        # The idea here is that if the 'skip_authors' field is true,
        # then -- even if there are no authors submitted --
        # we keep the authors ID list the same.
        if self.cleaned_data['skip_authors']:
            if self.instance.pk:
                if self.instance.authors.all():
                    self._restore_authors()

    def _restore_authors(self):
        self.cleaned_data['authors'] = [unicode(x.id) for x in self.instance.authors.all()]

    def save(self, commit=True):
        # We need to update the Video.tags descriptor manually because
        # Django's model forms does not (django.forms.models.construct_instance)
        self.instance.tags = self.cleaned_data['tags']
        instance = super(BulkEditVideoForm, self).save(commit=False)
        if commit:
            instance.save(update_index=False)
            self.save_m2m()
            instance._update_index = True
            index = connections['default'].get_unified_index().get_index(
                                                                 models.Video)
            index._enqueue_update(instance)
        return instance


class BulkEditVideoFormSet(BaseModelFormSet):
    def save_new_objects(self, commit):
        return []

    @property
    def _qs_cache(self):
        """
        Returns a dictionary of related objects that can be shared for form
        fields among the forms in the set.

        """
        # We use SharedQuerySet so that the form fields don't make fresh
        # querysets when they generate their choices.
        if not hasattr(self, '_real_qs_cache'):
            self._real_qs_cache = {
                'categories': BulkEditVideoForm.base_fields[
                                  'categories'].queryset._clone(
                                      utils.SharedQuerySet),
                'authors': BulkEditVideoForm.base_fields[
                                  'authors'].queryset._clone(
                                      utils.SharedQuerySet),
            }
        return self._real_qs_cache

    def _construct_form(self, i, **kwargs):
        """
        Use the same queryset for related objects on each form.

        """
        form = super(BulkEditVideoFormSet, self)._construct_form(i, **kwargs)
        form.fields['categories'].queryset = self._qs_cache['categories']
        form.fields['authors'].queryset = self._qs_cache['authors']
        return form

    def clean(self):
        BaseModelFormSet.clean(self)

        if any(self.errors):
            # don't bother doing anything if the form isn't valid
            return

        for form in list(self.deleted_forms):
            form.cleaned_data[DELETION_FIELD_NAME] = False
            form.instance.status = models.Video.REJECTED
            form.instance.save()
        bulk_edits = self.extra_forms[0].cleaned_data
        for key in list(bulk_edits.keys()): # get the list because we'll be
                                            # changing the dictionary
            if not bulk_edits[key]:
                del bulk_edits[key]
        bulk_action = self.data.get('bulk_action', '')
        if bulk_action:
            bulk_edits['action'] = bulk_action
        if bulk_edits:
            for form in self.initial_forms:
                if not form.cleaned_data['BULK']:
                    continue
                for key, value in bulk_edits.items():
                    if key == 'action': # do something to the video
                        method = getattr(self, 'action_%s' % value)
                        method(form)
                    elif key == 'tags':
                        form.cleaned_data[key] = value
                    elif key == 'categories':
                        # categories append, not replace
                        form.cleaned_data[key] = (
                            list(form.cleaned_data[key]) +
                            list(value))
                    elif key == 'authors':
                        form.cleaned_data[key] = value
                    else:
                        setattr(form.instance, key, value)

        self.can_delete = False

    def action_delete(self, form):
        form.instance.status = models.Video.REJECTED

    def action_approve(self, form):
        form.instance.status = models.Video.ACTIVE

    def action_unapprove(self, form):
        form.instance.status = models.Video.UNAPPROVED

    def action_feature(self, form):
        form.instance.status = models.Video.ACTIVE
        form.instance.last_featured = datetime.datetime.now()

    def action_unfeature(self, form):
        form.instance.last_featured = None


VideoFormSet = modelformset_factory(models.Video,
                                    form=BulkEditVideoForm,
                                    formset=BulkEditVideoFormSet,
                                    can_delete=True,
                                    extra=1)


class EditSettingsForm(forms.ModelForm):
    """
    """
    title = forms.CharField(label="Site Title", max_length=50)
    tagline = forms.CharField(label="Site Tagline", required=False,
                              max_length=4096,
                              help_text="Your title and tagline "
                              "define your site, both for humans and search "
                              "engines. Consider including key words so that "
                              "people can easily find your site.")
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
    playlists_enabled = forms.ChoiceField(
        label="Enable Playlists?",
        required=False,
        choices=(
            (0, 'No'),
            (1, 'Yes'),
            (2, 'Admins Only')))

    class Meta:
        model = models.SiteSettings
        exclude = ['site', 'status', 'admins', 'hide_get_started']


    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        if self.instance:
            self.initial['title'] = self.instance.site.name

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if not logo:
            return logo
        if self.instance and self.instance.logo and \
                self.instance.logo.name == logo.name:
            return logo
        if len(logo.name) > 60:
            name, ext = os.path.splitext(logo.name)
            logo.name = name[:60] + ext
        return logo

    def clean_background(self):
        background = self.cleaned_data.get('background')
        if not background:
            return background
        if self.instance and self.instance.background and \
                self.instance.background.name == background.name:
            return background
        if len(background.name) > 60:
            name, ext = os.path.splitext(background.name)
            background.name = name[:60] + ext
        return background

    def clean_playlists_enabled(self):
        return self.cleaned_data.get('playlists_enabled') or 0

    def save(self):
        sl = forms.ModelForm.save(self)
        if sl.logo:
            sl.logo.open()
            cf = ContentFile(sl.logo.read())
            sl.save_thumbnail_from_file(cf)
        sl.site.name = self.cleaned_data['title']
        sl.site.save()
        models.SiteSettings.objects.clear_cache()
        return sl

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


class CategoryForm(forms.ModelForm):
    parent = forms.models.ModelChoiceField(required=False,
                                    queryset=models.Category.objects.filter(
                                            site=settings.SITE_ID))

    class Meta:
        model = models.Category
        exclude = ['site']

    def _post_clean(self):
        forms.ModelForm._post_clean(self)
        try:
            self.instance.validate_unique()
        except forms.ValidationError, e:
            self._update_errors(e.message_dict)

class BaseCategoryFormSet(BulkFormSetMixin, BaseModelFormSet):
    @property
    def _qs_cache(self):
        """
        Returns a dictionary of related objects that can be shared for form
        fields among the forms in the set.

        """
        # We use SharedQuerySet so that the form fields don't make fresh
        # querysets when they generate their choices.
        if not hasattr(self, '_real_qs_cache'):
            self._real_qs_cache = {
                'parent': CategoryForm.base_fields['parent'].queryset._clone(
                                utils.SharedQuerySet),
            }
        return self._real_qs_cache

    def _construct_form(self, i, **kwargs):
        """
        Use the same queryset for related objects on each form.

        """
        form = super(BaseCategoryFormSet, self)._construct_form(i, **kwargs)
        form.fields['parent'].queryset = self._qs_cache['parent']
        return form

    def clean(self):
        BaseModelFormSet.clean(self)
        if not self.is_valid():
            return
        deleted_ids = set()
        ids_to_data = {}
        parents = {}
        # first pass: get the deleted items and map parents to items
        for i, data in enumerate(self.cleaned_data):
            ids_to_data[data['id']] = data
            if data.get('DELETE'):
                deleted_ids.add(data['id'])
            if data.get('parent'):
                parents.setdefault(data['parent'], set()).add(i)

        # second pass: check for cycles
        for data in self.cleaned_data:
            category = data
            s = set([category['id']])
            while category['parent']:
                if category['parent'] in s:
                    if len(s) == 1: # parent set to itself
                        error = ("A category cannot be its own parent. "
                                 "Please change the parent category")
                    else:
                        error = ("Some categories have conflicting parents.  "
                                 "Please change one or more of the parent "
                                 "categories")
                    names = ', '.join([category.name for category in s])
                    raise forms.ValidationError('%s: %s' % (error, names))
                category = ids_to_data[category['parent']]
                s.add(category['id'])

        # third pass: set children of deleted items to None:
        for parent in deleted_ids:
            if parent not in parents:
                continue
            for form_index in parents[parent]:
                form = self.forms[form_index]
                form.instance.parent = None
                form.instance.save()


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

class BaseFlatPageFormSet(BulkFormSetMixin, BaseModelFormSet):
    pass

FlatPageFormSet = modelformset_factory(FlatPage,
                                       form=FlatPageForm,
                                       formset=BaseFlatPageFormSet,
                                       can_delete=True,
                                       extra=0)

class AuthorForm(user_profile_forms.ProfileForm):
    role = forms.ChoiceField(choices=(
            ('user', 'User'),
            ('admin', 'Admin')),
            widget=forms.RadioSelect,
            required=False)
    website = forms.CharField(label='Website', required=False)
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
        fields = ['username', 'name', 'email', 'role', 'location', 'website',
                  'logo', 'description', 'password_f', 'password_f2']

    def __init__(self, *args, **kwargs):
        user_profile_forms.ProfileForm.__init__(self, *args, **kwargs)
        self.site_settings = models.SiteSettings.objects.get_current()
        if self.instance.pk:
            if self.site_settings.user_is_admin(self.instance):
                self.fields['role'].initial = 'admin'
            else:
                self.fields['role'].initial = 'user'
        else:
            for field_name in ['name', 'logo', 'location',
                               'description', 'website']:
                del self.fields[field_name]


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
        author = user_profile_forms.ProfileForm.save(self, **kwargs)
        if self.cleaned_data.get('password_f'):
            author.set_password(self.cleaned_data['password_f'])
        elif is_new:
            author.set_unusable_password()
        author.save()
        if self.cleaned_data.get('role'):
            if self.cleaned_data['role'] == 'admin':
                if not author.is_superuser:
                    self.site_settings.admins.add(author)
            else:
                self.site_settings.admins.remove(author)
            self.site_settings.save()
        return author

AuthorFormSet = modelformset_factory(User,
                                     form=AuthorForm,
                                     can_delete=True,
                                     extra=0)


class AddFeedForm(forms.ModelForm):
    auto_categories = BulkChecklistField(required=False,
                                         queryset=models.Category.objects.filter(
                                         site=settings.SITE_ID))
    auto_authors = BulkChecklistField(required=False,
                                      queryset=User.objects.order_by('username'))
    auto_approve = BooleanRadioField(required=False)

    class Meta:
        model = models.Feed
        fields = ('feed_url', 'auto_categories', 'auto_authors', 'auto_approve')

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(AddFeedForm, self).__init__(*args, **kwargs)

    def clean_feed_url(self):
        url = self.cleaned_data['feed_url']
        # Get a canonical URL from vidscraper
        scraped_feed = auto_feed(url, api_keys=API_KEYS)
        url = scraped_feed.url
        try:
            models.Feed.objects.get(feed_url=url, site=settings.SITE_ID)
        except models.Feed.DoesNotExist:
            pass
        else:
            raise ValidationError("Feed with this URL already exists.")
        return url

    def save(self, commit=True):
        self.instance.last_updated = datetime.datetime.now()
        self.instance.user = self.user
        self.instance.site_id = settings.SITE_ID
        self.instance.name = self.instance.feed_url
        instance = super(AddFeedForm, self).save(commit)
        feed_update.delay(instance.pk,
                          using=CELERY_USING,
                          clear_rejected=True)
        return instance


class EditThumbnailableForm(forms.ModelForm):
    thumbnail = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        super(EditThumbnailableForm, self).__init__(*args, **kwargs)
        if self.instance.has_thumbnail:
            path = self.instance.thumbnail_path
            if default_storage.exists(path):
                # Fake this being a field.
                self.initial['thumbnail'] = FieldFile(self.instance, FileField(), path)

    def save(self, commit=True):
        if 'thumbnail' in self.cleaned_data:
            if self.cleaned_data['thumbnail']:
                self.instance.save_thumbnail_from_file(self.cleaned_data['thumbnail'], update=False)
            else:
                self.instance.delete_thumbnail()
        return super(EditThumbnailableForm, self).save(commit)


class EditSourceForm(EditThumbnailableForm):
    auto_categories = BulkChecklistField(required=False,
                                         queryset=models.Category.objects.filter(
                                         site=settings.SITE_ID))
    auto_authors = BulkChecklistField(required=False,
                                      queryset=User.objects.order_by('username'))
    auto_approve = BooleanRadioField(required=False)


class EditFeedForm(EditSourceForm):
    class Meta:
        model = models.Feed
        fields = ('name', 'feed_url', 'webpage', 'thumbnail',
                  'auto_categories', 'auto_authors', 'auto_approve')


class EditSearchForm(EditSourceForm):
    query_string = forms.CharField()

    class Meta:
        model = models.SavedSearch
        fields = ('query_string', 'thumbnail', 'auto_categories',
                  'auto_authors', 'auto_approve')

