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
        action = self.cleaned_data['action']
        if action == self.NONE:
            return self.instance

        if action == self.APPROVE:
            self.approve(commit)
        elif action == self.REJECT:
            self.reject(commit)
        return self.instance

    def approve(self, commit=True):
        raise NotImplementedError

    def reject(self, commit=True):
        raise NotImplementedError


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
    def approve(self, commit=True):
        self.instance.status = Video.ACTIVE
        if commit:
            self.instance.save()

    def reject(self, commit=True):
        self.instance.status = Video.REJECTED
        if commit:
            self.instance.save()


class VideoLimitFormSet(forms.models.BaseModelFormSet):
    def clean(self):
        super(VideoLimitFormSet, self).clean()
        self._approved_count = sum(1 for f in self.forms
                                   if hasattr(self, 'cleaned_data') and
                                   f.cleaned_data['action'] == f.APPROVE)

        self._rejected_count = sum(1 for f in self.forms
                                   if hasattr(self, 'cleaned_data') and
                                   f.cleaned_data['action'] == f.REJECT)
        sitelocation = SiteLocation.objects.get_current()
        remaining_videos = sitelocation.get_tier().remaining_videos()
        if (SiteLocation.enforce_tiers() and remaining_videos < approved_count):
            raise ValidationError(_("You have selected %d videos, but may only "
                                    "approve %d more in your current tier. "
                                    "Upgrade to the next tier to approve more "
                                    "videos." % (approved_count,
                                                 remaining_videos)))
        


class RequestModelFormSet(forms.models.BaseModelFormSet):
    def __init__(self, request, **kwargs):
        self.request = request
        super(RequestModelFormSet, self).__init__(**kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs['request'] = self.request
        return super(RequestModelFormSet, self)._construct_form(i, **kwargs)
