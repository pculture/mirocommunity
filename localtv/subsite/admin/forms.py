from django import forms
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from localtv import models

class EditVideoForm(forms.Form):
    """
    """
    name = forms.CharField(max_length=250, required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)
    website_url = forms.URLField(required=False)
    video_id = forms.CharField(widget=forms.HiddenInput)
    thumbnail = forms.ImageField(required=False)
    tags = forms.CharField(required=False)
    categories = forms.ModelMultipleChoiceField(queryset=models.Category.objects,
                                                required=False)
    authors = forms.ModelMultipleChoiceField(queryset=models.Author.objects,
                                             required=False)

    @classmethod
    def create_from_video(cls, video):
        self = cls()
        self.initial['name'] = video.name
        self.initial['description'] = video.description
        self.initial['website_url'] = video.website_url
        self.initial['video_id'] = video.id
        self.initial['tags'] = ', '.join(video.tags.values_list('name',
                                                                flat=True))
        self.fields['categories'].queryset = models.Category.objects.filter(
            site=video.site)
        self.initial['categories'] = [category.pk for category in video.categories.all()]
        self.fields['authors'].queryset = models.Author.objects.filter(
            site=video.site)
        self.initial['authors'] = [author.pk for author in video.authors.all()]

        return self

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
    class Meta:
        model = models.Author
        exclude = ['site']


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
