from django import forms
from django.forms.models import BaseModelFormSet, modelformset_factory
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
                self.instance.thumbnail_url = \
                    self.cleaned_data['thumbnail_url'] = ''
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


class BulkEditVideoForm(EditVideoForm):
    bulk = forms.BooleanField(required=False)
    name = forms.CharField(widget=forms.TextInput(
            attrs={'class': 'large_field'}),
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
                                         widget=forms.TextInput(
            attrs={'class': 'large_field'}))

    class Meta:
        model = models.Video
        fields = ('name', 'description', 'thumbnail', 'thumbnail_url', 'tags',
                  'categories', 'authors', 'when_published', 'file_url')

    def __init__(self, *args, **kwargs):
        EditVideoForm.__init__(self, *args, **kwargs)
        self.fields['categories'].queryset = \
            self.fields['categories'].queryset.filter(
            site=self.instance.site)

VideoFormSet = modelformset_factory(models.Video,
                                    form=BulkEditVideoForm,
                                    can_delete=True,
                                    extra=1)


class EditTitleForm(forms.Form):
    """
    """
    title = forms.CharField(label="Site Title")
    tagline = forms.CharField(label="Site Tagline")
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
    sidebar = forms.CharField(label="Sidebar Blurb (use html)",
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
    layout = forms.ChoiceField(label="Front Page Layout", choices=(
            ("scrolling", "Scrolling big features"),
            ("list", "List style"),
            ("categorized", "Categorized layout")),
                               help_text=" (note: with the scrolling and categorized layouts, you will need to provide hi-quality images for each featured video)")
    display_submit_button = forms.BooleanField(
        label="Display the 'submit a video' nav item",
        required=False)
    submission_requires_login = forms.BooleanField(
        label="Require users to login to submit a video",
        required=False)
    css = forms.CharField(label="Custom CSS",
                          help_text="Here you can append your own CSS to customize your site.",
                          widget=forms.Textarea, required=False)

    @classmethod
    def create_from_sitelocation(cls, sitelocation):
        self = cls()
        self.initial['css'] = sitelocation.css
        self.initial['layout'] = sitelocation.frontpage_style
        self.initial['display_submit_button'] = sitelocation.display_submit_button
        self.initial['submission_requires_login'] = sitelocation.submission_requires_login
        return self

    def save_to_sitelocation(self, sitelocation):
        if not self.is_valid():
            raise RuntimeError("cannot save invalid form")
        logo = self.cleaned_data.get('logo')
        if logo is not None:
            sitelocation.logo.save(logo.name, logo, save=False)
        background = self.cleaned_data.get('background')
        if background is not None:
            sitelocation.background.save(background.name, background, save=False)
        sitelocation.css = self.cleaned_data.get('css', '')
        sitelocation.frontpage_style = self.cleaned_data['layout']
        sitelocation.display_submit_button = self.cleaned_data['display_submit_button']
        sitelocation.submission_requires_login = self.cleaned_data['submission_requires_login']
        sitelocation.save()

class CategoryForm(forms.ModelForm):
    class Meta:
        model = models.Category
        exclude = ['site']

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)

        site = Site.objects.get_current()
        self.fields['parent'].queryset = models.Category.objects.filter(
            site=site)

class AuthorForm(forms.ModelForm):
    logo = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'logo']

    def save(self, **kwargs):
        author = forms.ModelForm.save(self, **kwargs)
        if self.cleaned_data.get('logo'):
            logo = self.cleaned_data['logo']
            print 'going to save', logo
            try:
                profile = author.get_profile()
            except models.Profile.DoesNotExist:
                profile = models.Profile.objects.create(
                    user=author)

            profile.logo = logo
            profile.save()
        return author

class AddUserForm(forms.Form):
    user = forms.CharField(
        help_text=("You can enter a user name, an OpenID, or an e-mail "
                   "address in this field"))

    def clean_user(self):
        value = self.cleaned_data['user']

        if value.startswith('http://') or value.startswith('https://'):
            # possibly an OpenID
            openid_users = models.OpenIdUser.objects.filter(url=value)
            if openid_users:
                return [oid.user for oid in openid_users]

        if '@' in value:
            # possibly an e-mail address
            users = User.objects.filter(email=value)
            if users:
                return users

        users = User.objects.filter(username=value)
        if users:
            return users
        else:
            raise forms.ValidationError('Could not find a matching user')

class VideoServiceForm(forms.Form):
    URLS = (
        ('YouTube', 'http://www.youtube.com/rss/user/%s/videos.rss'),
        ('blip.tv', 'http://%s.blip.tv/rss'),
        ('Vimeo', 'http://www.vimeo.com/%s/videos/rss'),
         )
    service = forms.ChoiceField(
        choices = enumerate([service for service, url in URLS]))
    username = forms.CharField(
        initial="e.g. openvideoalliance")

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.fields['username'].widget.attrs.update(
            {'onfocus': 'clearText(this)',
             'class': 'large_field'})

    def feed_url(self):
        index = int(self.cleaned_data['service'])
        return self.URLS[index][1] % self.cleaned_data['username']
