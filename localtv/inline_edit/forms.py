# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

from django import forms
from django.contrib.auth.models import User
from django.contrib import comments
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_unicode

from tagging.forms import TagField

from localtv import models, util

from localtv.admin.forms import EditVideoForm, BulkChecklistField

Comment = comments.get_model()

class VideoNameForm(forms.ModelForm):
    class Meta:
        model = models.Video
        fields = ('name',)

class VideoWhenPublishedForm(forms.ModelForm):
    when_published = forms.DateTimeField(
        label="When Published",
        required=False,
        help_text='Format: yyyy-mm-dd hh:mm:ss')

    class Meta:
        model = models.Video
        fields = ('when_published',)

class VideoAuthorsForm(forms.ModelForm):
    authors = BulkChecklistField(User.objects,
                                 required=False)
    class Meta:
        model = models.Video
        fields = ('authors',)

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        self.fields['authors'].queryset = \
            self.fields['authors'].queryset.order_by('username')

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
    tags = TagField(required=False, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        self.initial['tags'] = util.get_or_create_tags(self.instance.tags)

    def save(self, *args, **kwargs):
        self.instance.tags = self.cleaned_data.get('tags')
        return forms.ModelForm.save(self, *args, **kwargs)

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

class VideoEditorsComment(forms.Form):
    editors_comment = forms.CharField(required=False,
                                      widget=forms.Textarea)

    def __init__(self, data=None, instance=None):
        forms.Form.__init__(self, data)
        self.instance = instance
        if self.instance:
            self.content_type = ContentType.objects.get_for_model(
                self.instance)
            comments = Comment.objects.filter(
                site=self.instance.site,
                content_type=self.content_type,
                object_pk=unicode(self.instance.pk),
                flags__flag='editors comment')
            if not comments.count():
                self.comment = None
            else:
                self.comment = comments[0]
                for extra in list(comments[1:]):
                    extra.delete()
                self.initial['editors_comment'] = self.comment.comment
        else:
            self.comment = None

    def save(self, commit=True):
        text = self.cleaned_data.get('editors_comment', '')
        if self.comment:
            self.comment.delete()
        if not text:
            return
        self.comment = comments.get_model()(
            comment=self.cleaned_data['editors_comment'],
            content_type=self.content_type,
            object_pk=self.instance.pk,
            is_removed=True, # don't put it in the queue
            is_public=False)
        def save_m2m():
            comments.models.CommentFlag.objects.get_or_create(
                comment=self.comment,
                user=self.comment.user,
                flag='editors comment')
        if commit:
            self.comment.save()
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return self.comment

class VideoThumbnailForm(EditVideoForm):
    pass
