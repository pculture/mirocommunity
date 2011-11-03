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
from django.utils.translation import ugettext_lazy as _


class CommentModerationForm(forms.ModelForm):
    APPROVE = 'approve'
    REMOVE = 'remove'
    NONE = ''

    ACTION_CHOICES = (
        (APPROVE, _('Approve')),
        (REMOVE, _('Remove')),
        (NONE, _('No action')),
    )

    action = forms.ChoiceField(choices=ACTION_CHOICES, initial=NONE)

    class Meta:
        fields = []

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(CommentModerationForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        action = self.cleaned_data['action']

        if action == self.NONE:
            return self.instance

        if action == self.APPROVE:
            self.instance.is_removed = False
            self.instance.is_public = True
            flag = CommentFlag.MODERATOR_APPROVAL
        elif action == self.REMOVE:
            self.instance.is_removed = True
            flag = CommentFlag.MODERATOR_DELETION

        flag, created = CommentFlag.objects.get_or_create(
            comment=self.instance,
            user=self.request.user,
            flag=flag
        )

        self.instance.save()

        comments.signals.comment_was_flagged.send(
            sender=self.instance.__class__,
            comment=self.instance,
            flag=flag,
            created=created,
            request=self.request
        )

        return self.instance


class RequestModelFormSet(forms.models.BaseModelFormSet):
    def __init__(self, request, **kwargs):
        self.request = request
        super(RequestModelFormSet, self).__init__(**kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs['request'] = self.request
        return super(RequestModelFormSet, self)._construct_form(i, **kwargs)


CommentModerationFormSet = forms.models.modelformset_factory(
                               model=Comment,
                               formset=RequestModelFormSet,
                               form=CommentModerationForm,
                               extra=0,
                               max_num=0
                           )
