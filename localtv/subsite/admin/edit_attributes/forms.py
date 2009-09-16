from django import forms
from django.contrib.auth.models import User

from localtv import models
from localtv.subsite.admin.forms import (TagField, TagAreaWidget,
                                         BulkChecklistField)


class FeedNameForm(forms.ModelForm):
    class Meta:
        model = models.Feed
        fields = ('name',)


class FeedAutoCategoriesForm(forms.ModelForm):
    class Meta:
        model = models.Feed
        fields = ('auto_categories',)

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        self.fields['auto_categories'].queryset = \
            self.fields['auto_categories'].queryset.filter(
            site=self.instance.site)


class FeedAutoAuthorsForm(forms.ModelForm):
    class Meta:
        model = models.Feed
        fields = ('auto_authors',)

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)

class VideoNameForm(forms.ModelForm):
    class Meta:
        model = models.Video
        fields = ('name',)

class VideoWhenPublishedForm(forms.ModelForm):
    class Meta:
        model = models.Video
        fields = ('when_published',)

class VideoAuthorsForm(forms.ModelForm):
    authors = BulkChecklistField(User.objects,
                                 required=False)
    class Meta:
        model = models.Video
        fields = ('authors',)

class VideoCategoriesForm(forms.ModelForm):
    categories = BulkChecklistField(models.Category.objects,
                                    required=False)
    class Meta:
        model = models.Video
        fields = ('categories',)

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        self.fields['categories'].queryset = \
            self.fields['categories'].queryset.filter(
            site=self.instance.site)

class VideoTagsForm(forms.ModelForm):
    tags = TagField(required=False, widget=TagAreaWidget)
    class Meta:
        model = models.Video
        fields = ('tags',)

class VideoDescriptionField(forms.ModelForm):
    class Meta:
        model = models.Video
        fields = ('description',)

class VideoWebsiteUrlField(forms.ModelForm):
    class Meta:
        model = models.Video
        fields = ('website_url',)
