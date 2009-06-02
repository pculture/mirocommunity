from django import forms


class EditVideoForm(forms.Form):
    """
    """
    name = forms.CharField(max_length=250)
    description = forms.CharField(widget=forms.Textarea)
    website_url = forms.URLField()
    video_id = forms.CharField(widget=forms.HiddenInput)

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
                            widget=forms.Textarea)

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
        sitelocation.tagline = self.cleaned_data['tagline']
        sitelocation.about_html = self.cleaned_data['about']
        sitelocation.site.save()
        sitelocation.save()


class EditSidebarForm(forms.Form):
    blurb = forms.CharField(label="Sidebar Blurb (use html)",
                            widget=forms.Textarea)

    @classmethod
    def create_from_sitelocation(cls, sitelocation):
        self = cls()
        self.initial['blurb'] = sitelocation.sidebar_html
        return self

    def save_to_sitelocation(self, sitelocation):
        if not self.is_valid():
            raise RuntimeError("cannot save invalid form")
        sitelocation.sidebar_html = self.cleaned_data['blurb']
        sitelocation.save()


class EditMiscDesignForm(forms.Form):
    logo = forms.ImageField(label="Logo Image")
    background = forms.ImageField(label="Background Image")
    theme = forms.ChoiceField(label="Color Theme", choices=(
            ("day", "Day"),
            ("night", "Night")))
    layout = forms.ChoiceField(label="Front Page Layout", choices=(
            ("scrolling", "Scrolling big features (note: with this mode, you will need to provide hi-quality images for each featured video)."),
            ("list", "List style"),
            ("categorized", "Categorized layout")))
    css = forms.CharField(label="Custom CSS",
                          help_text="Here you can append your own CSS to customize your site.",
                          widget=forms.Textarea)

    @classmethod
    def create_from_sitelocation(cls, sitelocation):
        self = cls()
        self.initial['blurb'] = sitelocation.sidebar_html
        return self

    def save_to_sitelocation(self, sitelocation):
        if not self.is_valid():
            raise RuntimeError("cannot save invalid form")
        sitelocation.sidebar_html = self.cleaned_data['blurb']
        sitelocation.save()
