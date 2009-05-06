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
