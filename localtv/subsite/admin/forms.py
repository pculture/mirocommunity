from django import forms

class EditVideoForm(forms.Form):
    """
    """
    name = forms.CharField(max_length=250)
    description = forms.CharField(widget=forms.Textarea)
    website_url = forms.URLField()
    video_id = forms.CharField(widget=forms.HiddenInput)
    thumbnail = forms.ImageField(required=False)

    @classmethod
    def create_from_video(cls, video):
        self = cls()
        self.initial['name'] = video.name
        self.initial['description'] = video.description
        self.initial['website_url'] = video.website_url
        self.initial['video_id'] = video.id

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
                             widget=forms.Textarea, required=False)

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
            ("scrolling", "Scrolling big features (note: with this mode, you will need to provide hi-quality images for each featured video)."),
            ("list", "List style")))
    #        ("categorized", "Categorized layout")))
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
