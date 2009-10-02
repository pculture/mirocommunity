import re
import feedparser

from django import forms
from django.forms.formsets import BaseFormSet
from django.forms.models import modelformset_factory, BaseModelFormSet
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from localtv import models

class TagWidgetMixin:
    def render(self, name, value, attrs=None):
        if isinstance(value, basestring):
            return self.__class__.__bases__[-1].render(self, name, value,
                                                       attrs)
        if value is None:
            value = []
        return self.__class__.__bases__[-1].render(
            self, name,
            ', '.join(models.Tag.objects.filter(pk__in=value).values_list(
                    'name', flat=True)),
            attrs)

class TagWidget(TagWidgetMixin, forms.TextInput):
    pass

class TagAreaWidget(TagWidgetMixin, forms.Textarea):
    pass

class TagField(forms.CharField):
    widget = TagWidget

    def clean(self, value):
        if not value:
            return []
        names = [name.strip() for name in value.split(',')]
        tags = []
        for name in names:
            tag, created = models.Tag.objects.get_or_create(name=name)
            tags.append(tag)
        return tags

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
                                 queryset=User.objects)
    auto_approve = BooleanRadioField(required=False)

    class Meta:
        model = models.Source
        fields = ('auto_approve', 'auto_categories', 'auto_authors')

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        if 'auto_approve' in self.initial:
            self.initial['auto_approve'] = bool(self.initial['auto_approve'])
        site = Site.objects.get_current()
        self.fields['auto_categories'].queryset = \
            self.fields['auto_categories'].queryset.filter(
            site=site)

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
            form.fields['bulk'] = forms.BooleanField(required=False)
        BaseFormSet.add_fields(self, form, index)


SourceFormset = modelformset_factory(models.Source,
                                     form=SourceForm,
                                     formset=BaseSourceFormSet,
                                     can_delete=True,
                                     extra=1)


class BulkEditVideoForm(EditVideoForm):
    bulk = forms.BooleanField(required=False)
    name = forms.CharField(
        required=False)
    file_url = forms.CharField(widget=forms.TextInput(
            attrs={'class': 'large_field'}),
                               required=False)
    thumbnail_url = forms.CharField(widget=forms.TextInput(
            attrs={'class': 'large_field'}),
                                    required=False)
    tags = TagField(required=False,
                    widget=TagAreaWidget)
    categories = BulkChecklistField(models.Category.objects, required=False)
    authors = BulkChecklistField(User.objects, required=False)
    when_published = forms.DateTimeField(required=False,
                                         widget=forms.DateTimeInput(
            attrs={'class': 'large_field'}))

    class Meta:
        model = models.Video
        fields = ('name', 'description', 'thumbnail', 'thumbnail_url', 'tags',
                  'categories', 'authors', 'when_published', 'file_url')

    def __init__(self, *args, **kwargs):
        EditVideoForm.__init__(self, *args, **kwargs)
        site = Site.objects.get_current()
        self.fields['categories'].queryset = \
            self.fields['categories'].queryset.filter(
            site=site)

VideoFormSet = modelformset_factory(models.Video,
                                    form=BulkEditVideoForm,
                                    can_delete=True,
                                    extra=1)


class EditTitleForm(forms.Form):
    """
    """
    title = forms.CharField(label="Site Title")
    tagline = forms.CharField(label="Site Tagline", required=False)
    about = forms.CharField(label="About Us Page (use html)",
                            widget=forms.Textarea, required=False)

    @classmethod
    def create_from_sitelocation(cls, sitelocation):
        self = cls()
        self.initial['title'] = sitelocation.site.name
        self.initial['tagline'] = sitelocation.tagline
        self.initial['about'] = sitelocation.about_html
        return self

    def save_to_sitelocation(self, sitelocation):
        if not self.is_valid():
            raise RuntimeError("cannot save invalid form")
        sitelocation.site.name = self.cleaned_data['title']
        sitelocation.tagline = self.cleaned_data.get('tagline', '')
        sitelocation.about_html = self.cleaned_data.get('about', '')
        sitelocation.site.save()
        sitelocation.save()


class EditSidebarForm(forms.Form):
    sidebar = forms.CharField(label="Sidebar Blurb (use htm)",
                            widget=forms.Textarea, required=False)
    footer = forms.CharField(label="Footer Blurb (use html)",
                             widget=forms.Textarea, required=False,
                             help_text="In addition to any footer text you "
                             "would like to add, we suggest using this space "
                             "to paste in a Google Analytics tracking code, "
                             "which will provide excellent statistics on "
                             "usage of your site.")

    @classmethod
    def create_from_sitelocation(cls, sitelocation):
        self = cls()
        self.initial['sidebar'] = sitelocation.sidebar_html
        self.initial['footer'] = sitelocation.footer_html
        return self

    def save_to_sitelocation(self, sitelocation):
        if not self.is_valid():
            raise RuntimeError("cannot save invalid form")
        sitelocation.sidebar_html = self.cleaned_data.get('sidebar', '')
        sitelocation.footer_html = self.cleaned_data.get('footer', '')
        sitelocation.save()


class EditMiscDesignForm(forms.Form):
    logo = forms.ImageField(label="Logo Image", required=False)
    background = forms.ImageField(label="Background Image", required=False)
    #theme = forms.ChoiceField(label="Color Theme", choices=(
    #        ("day", "Day"),
    #        ("night", "Night")))
    layout = forms.ChoiceField(
        label="Front Page Layout", choices=(
            ("scrolling", "Scrolling big features"),
            ("list", "List style"),
            ("categorized", "Categorized layout")),
        help_text=(" (note: with the scrolling and categorized layouts, you "
                   "will need to provide hi-quality images for each featured "
                   "video)"))
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

    @classmethod
    def create_from_sitelocation(cls, sitelocation):
        self = cls()
        self.initial['css'] = sitelocation.css
        self.initial['layout'] = \
            sitelocation.frontpage_style
        self.initial['display_submit_button'] = \
            sitelocation.display_submit_button
        self.initial['submission_requires_login'] = \
            sitelocation.submission_requires_login
        return self

    def save_to_sitelocation(self, sitelocation):
        if not self.is_valid():
            raise RuntimeError("cannot save invalid form")
        logo = self.cleaned_data.get('logo')
        if logo is not None:
            sitelocation.logo.save(logo.name, logo, save=False)
        background = self.cleaned_data.get('background')
        if background is not None:
            sitelocation.background.save(background.name, background,
                                         save=False)
        sitelocation.css = self.cleaned_data.get('css', '')
        sitelocation.frontpage_style = self.cleaned_data['layout']
        sitelocation.display_submit_button = \
            self.cleaned_data['display_submit_button']
        sitelocation.submission_requires_login = \
            self.cleaned_data['submission_requires_login']
        sitelocation.save()


class EditCommentsForm(forms.ModelForm):
    class Meta:
        model = models.SiteLocation
        fields = ('screen_all_comments', 'comments_email_admins',
                  'comments_required_login')


class CategoryForm(forms.ModelForm):
    class Meta:
        model = models.Category
        exclude = ['site']

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)

        site = Site.objects.get_current()
        self.fields['parent'].queryset = models.Category.objects.filter(
            site=site)


class BaseCategoryFormSet(BaseModelFormSet):

    def add_fields(self, form, i):
        BaseModelFormSet.add_fields(self, form, i)
        if i < self.initial_form_count():
            form.fields['bulk'] = forms.BooleanField(required=False)


CategoryFormSet = modelformset_factory(models.Category,
                                       form=CategoryForm,
                                       formset=BaseCategoryFormSet,
                                       can_delete=True,
                                       extra=0)


class AuthorForm(forms.ModelForm):
    role = forms.ChoiceField(choices=(
            ('user', 'User'),
            ('admin', 'Admin')),
                             required=False)
    logo = forms.ImageField(required=False)
    description = forms.CharField(
        widget=forms.Textarea,
        required=False)
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
            except models.Profile.DoesNotExist:
                profile = models.Profile.objects.create(
                    user=self.instance)
            self.fields['description'].initial = profile.description

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
        author = forms.ModelForm.save(self, **kwargs)
        if self.cleaned_data.get('password_f'):
            author.set_password(self.cleaned_data['password_f'])
        else:
            author.set_unusable_password()
        author.save()
        if 'logo' in self.cleaned_data or 'description' in self.cleaned_data:
            try:
                profile = author.get_profile()
            except models.Profile.DoesNotExist:
                profile = models.Profile.objects.create(
                    user=author)
        if self.cleaned_data.get('logo'):
            logo = self.cleaned_data['logo']
            profile.logo = logo
            profile.save()
        if 'description' in self.cleaned_data:
            profile.description = self.cleaned_data['description']
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
                r'^(http://)?(www\.)?youtube\.com/profile\?(\w+=\w+&)*'
                r'user=(?P<name>\w+)'),
         'youtube'),
        (re.compile(r'^(http://)?(www\.)?youtube\.com/(user/)?(?P<name>\w+)$'),
         'youtube'),
        (re.compile(r'^(http://)?(www\.)?(?P<name>\w+)\.blip\.tv'), 'blip'),
        (re.compile(r'^(http://)?(www\.)?vimeo\.com/(?P<name>\w+)'), 'vimeo'),
        )

    SERVICE_FEEDS = {
        'youtube': 'http://www.youtube.com/rss/user/%s/videos.rss',
        'blip': 'http://%s.blip.tv/rss',
        'vimeo': 'http://www.vimeo.com/%s/videos/rss',
        }

    feed_url = forms.URLField(required=True,
                              widget=forms.TextInput(
            attrs={'class': 'livesearch_feed_url'}))

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
                                      site=site,
                                      status=models.FEED_STATUS_ACTIVE):
            raise forms.ValidationError(
                'That feed already exists on this site.')

        parsed = feedparser.parse(value)
        if not parsed.feed and parsed.entries:
            raise forms.ValidationError('It does not appear that %s is an '
                                        'RSS/Atom feed URL.')

        # drop the parsed data into cleaned_data so that other code can re-use
        # the data
        self.cleaned_data['parsed_feed'] = parsed

        return value
