from django import forms

from localtv import models


class FeedNameForm(forms.ModelForm):
    class Meta:
        model = models.Feed
        fields = ('name')
