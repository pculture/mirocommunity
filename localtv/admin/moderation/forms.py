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

import datetime

from django import forms
from django.contrib import comments
from django.contrib.comments.models import CommentFlag, Comment
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from localtv.models import Video, SiteLocation


class ModerationForm(forms.ModelForm):
    APPROVE = 'approve'
    REJECT = 'reject'
    NONE = 'none'

    ACTION_CHOICES = (
        (APPROVE, _('Approve')),
        (REJECT, _('Reject')),
        (NONE, _('No action')),
    )

    action = forms.ChoiceField(choices=ACTION_CHOICES, initial=NONE,
                               widget=forms.RadioSelect)

    class Meta:
        fields = []

    def save(self, commit=True):
        self.handle_action(self.cleaned_data['action'], commit)
        return self.instance

    def approve(self, commit=True):
        raise NotImplementedError

    def reject(self, commit=True):
        raise NotImplementedError

    def handle_action(self, action, commit=True):
        if action == self.NONE:
            return
        elif action == self.APPROVE:
            self.approve(commit)
        elif action == self.REJECT:
            self.reject(commit)


class CommentModerationForm(ModerationForm):
    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(CommentModerationForm, self).__init__(*args, **kwargs)

    def flag_comment(self, flag):
        flag, created = CommentFlag.objects.get_or_create(
            comment=self.instance,
            user=self.request.user,
            flag=flag
        )
        comments.signals.comment_was_flagged.send(
            sender=self.instance.__class__,
            comment=self.instance,
            flag=flag,
            created=created,
            request=self.request
        )

    def approve(self, commit=True):
        self.instance.is_removed = False
        self.instance.is_public = True
        self.instance.save()
        self.flag_comment(CommentFlag.MODERATOR_APPROVAL)

    def reject(self, commit=True):
        self.instance.is_removed = True
        self.instance.save()
        self.flag_comment(CommentFlag.MODERATOR_DELETION)


class VideoModerationForm(ModerationForm):
    FEATURE = 'feature'

    ACTION_CHOICES = ModerationForm.ACTION_CHOICES[:-1] + (
        (FEATURE, _('Feature')),
    ) + ModerationForm.ACTION_CHOICES[-1:]

    action = forms.ChoiceField(choices=ACTION_CHOICES,
                               initial=ModerationForm.NONE,
                               widget=forms.RadioSelect)

    def approve(self, commit=True):
        if not self.instance.is_active():
            self.instance.status = Video.ACTIVE
            self.instance.when_approved = datetime.datetime.now()
            if commit:
                self.instance.save()

    def reject(self, commit=True):
        self.instance.status = Video.REJECTED
        if commit:
            self.instance.save()

    def feature(self, commit=True):
        self.approve(commit=False)
        self.instance.last_featured = datetime.datetime.now()
        if commit:
            self.instance.save()

    def handle_action(self, action, commit=True):
        if action == self.FEATURE:
            self.feature(commit)
        else:
            super(VideoModerationForm, self).handle_action(action, commit)


class VideoLimitFormSet(forms.models.BaseModelFormSet):
    def clean(self):
        super(VideoLimitFormSet, self).clean()
        self._approved_count = sum(1 for f in self.forms
                                   if hasattr(self, 'cleaned_data') and
                                   f.cleaned_data['action'] == f.APPROVE)

        self._rejected_count = sum(1 for f in self.forms
                                   if hasattr(self, 'cleaned_data') and
                                   f.cleaned_data['action'] == f.REJECT)
        self._featured_count = sum(1 for f in self.forms
                                   if hasattr(self, 'cleaned_data') and
                                   f.cleaned_data['action'] == f.FEATURE)
        sitelocation = SiteLocation.objects.get_current()
        remaining_videos = sitelocation.get_tier().remaining_videos()
        approved_count = self._approved_count + self._featured_count
        if (SiteLocation.enforce_tiers() and remaining_videos < approved_count):
            raise ValidationError(_("You have selected %d videos, but may only "
                                    "approve %d more in your current tier. "
                                    "Please upgrade your account to increase "
                                    "your limit, or unapprove some older videos"
                                    " to make space for newer ones." % (
                                    approved_count, remaining_videos)))
        


class RequestModelFormSet(forms.models.BaseModelFormSet):
    def __init__(self, request, **kwargs):
        self.request = request
        super(RequestModelFormSet, self).__init__(**kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs['request'] = self.request
        return super(RequestModelFormSet, self)._construct_form(i, **kwargs)
