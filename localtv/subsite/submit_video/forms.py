from django import forms

from localtv import models

class SubmitVideoForm(forms.Form):
    website_url = forms.URLField()
    tags = forms.CharField()


class ScrapedSubmitVideoForm(forms.Form):
    website_url = forms.URLField()
    tags = forms.CharField()
    file_url = forms.URLField()
    embed = forms.CharField()
    name = forms.CharField(max_length=250)
    description = forms.CharField(widget=forms.widgets.Textarea)
    #categories = forms.ModelMultipleChoiceField(models.Category.objects.all())
