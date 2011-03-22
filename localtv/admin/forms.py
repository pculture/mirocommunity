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

from localtv import models
from localtv import util
import localtv.tiers
from localtv.user_profile import forms as user_profile_forms


Profile = util.get_profile_model()

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
            if form.cleaned_data['BULK'] and \
                    not self._should_delete_form(form):
                yield form

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
            if (thumbnail_url and not
                models.Video.objects.get(id=self.instance.id).thumbnail_url == thumbnail_url):
                self.instance.thumbnail_url = thumbnail_url
                try:
                    self.instance.save_thumbnail()
                except models.CannotOpenImageUrl:
                    pass # wwe'll get it in a later update
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
    categories = BulkChecklistField(models.Category.objects,
                                    required=False)
    authors = BulkChecklistField(User.objects,
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

    _categories_queryset = None
    _authors_queryset = None

    def __init__(self, *args, **kwargs):
        EditVideoForm.__init__(self, *args, **kwargs)
        site = Site.objects.get_current()

        # cache the querysets so that we don't hit the DB for each form
        if self.__class__._categories_queryset is None:
            self.__class__._categories_queryset = util.MockQueryset(
                models.Category.objects.filter(site=site))
        if self.__class__._authors_queryset is None:
            self.__class__._authors_queryset = util.MockQueryset(
                User.objects.order_by('username'))
        self.fields['categories'].queryset = \
            self.__class__._categories_queryset
        self.fields['authors'].queryset = \
            self.__class__._authors_queryset

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

VideoFormSet = modelformset_factory(models.Video,
                                    form=BulkEditVideoForm,
                                    can_delete=True,
                                    extra=1)


class EditSettingsForm(forms.ModelForm):
    """
    """
    title = forms.CharField(label="Site Title", max_length=50)
    tagline = forms.CharField(label="Site Tagline", required=False,
                              max_length=250,
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
        model = models.SiteLocation
        exclude = ['site', 'status', 'admins', 'tier_name', 'hide_get_started']


    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        if self.instance:
            self.initial['title'] = self.instance.site.name
        if (not localtv.models.SiteLocation.objects.get_current().enforce_tiers()
            or localtv.tiers.Tier.get().permit_custom_css()):
            pass # Sweet, CSS is permitted.
        else:
            # Uh-oh: custom CSS is not permitted!
            #
            # To handle only letting certain paid users edit CSS,
            # we do two things.
            #
            # 1. Cosmetically, we set the CSS editing box's CSS class
            # to be 'hidden'. (We have some CSS that makes it not show
            # up.)
            css_field = self.fields['css']
            css_field.label += ' (upgrade to enable this form field)'
            css_field.widget.attrs['readonly'] = True
            #
            # 2. In validation, we make sure that changing the CSS is
            # rejected as invalid if the site does not have permission
            # to do that.

    def clean_css(self):
        css = self.cleaned_data.get('css')
        # Does thes SiteLocation permit CSS modifications? If so,
        # return the data the user inputted.
        if (not localtv.models.SiteLocation.objects.get_current().enforce_tiers() or
            localtv.tiers.Tier.get().permit_custom_css()):
            return css # no questions asked

        # We permit the value if it's the same as self.instance has:
        if self.instance.css == css:
            return css

        # Otherwise, reject the change.
        self.data['css'] = self.instance.css
        raise ValidationError("To edit CSS for your site, you have to upgrade.")

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
        models.SiteLocation.objects.clear_cache()
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

class CategoryForm(forms.ModelForm):
    class Meta:
        model = models.Category
        exclude = ['site']

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)

        self.site = Site.objects.get_current()
        self.fields['parent'].queryset = models.Category.objects.filter(
            site=self.site)

    def _post_clean(self):
        forms.ModelForm._post_clean(self)
        try:
            self.instance.validate_unique()
        except forms.ValidationError, e:
            self._update_errors(e.message_dict)

class BaseCategoryFormSet(BulkFormSetMixin, BaseModelFormSet):

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
        self.sitelocation = models.SiteLocation.objects.get_current()
        if self.instance.pk:
            if self.sitelocation.user_is_admin(self.instance):
                self.fields['role'].initial = 'admin'
            else:
                self.fields['role'].initial = 'user'
        else:
            for field_name in ['name', 'logo', 'location',
                               'description', 'website']:
                del self.fields[field_name]
        ## Add a note to the 'role' help text indicating how many admins
        ## are permitted with this kind of account.
        tier = localtv.tiers.Tier.get()
        if tier.admins_limit() is not None:
            message = 'With a %s, you may have %d administrator%s.' % (
                models.SiteLocation.objects.get_current().get_tier_name_display(),
                tier.admins_limit(),
                django.template.defaultfilters.pluralize(tier.admins_limit()))
            self.fields['role'].help_text = message

    def clean_role(self):
        if not localtv.models.SiteLocation.objects.get_current().enforce_tiers():
            return self.cleaned_data['role']

        # If the user tried to create an admin, but the tier does not
        # permit creating another admin, raise an error.
        permitted_admins = localtv.tiers.Tier.get().admins_limit()
        if self.cleaned_data['role'] == 'admin' and permitted_admins is not None:
            num_admins = localtv.tiers.number_of_admins_including_superuser()

            if (permitted_admins is not None) and num_admins >= permitted_admins:
                raise ValidationError("You already have %d admin%s in your site. Upgrade to have access to more." % (
                    permitted_admins,
                    django.template.defaultfilters.pluralize(permitted_admins)))
        # Otherwise, things seem good!
        return self.cleaned_data['role']

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
