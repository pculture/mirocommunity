from django import forms

from localtv import models


class FeedNameForm(forms.ModelForm):
    class Meta:
        model = models.Feed
        fields = ('name')


class FeedAutoCategoriesForm(forms.ModelForm):
    class Meta:
        model = models.Feed
        fields = ('auto_categories')


class FeedAutoAuthorsForm(forms.ModelForm):
    class Meta:
        model = models.Feed
        fields = ('auto_authors')
