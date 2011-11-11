# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
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

from localtv.models import SiteLocation
from notification import models as notification


class NotificationsForm(forms.Form):

    CHOICES = (
        ('video_approved', 'A video you submitted was approved'),
        ('video_comment', 'Someone left a comment on your video'),
        ('comment_post_comment',
         'Someone left a comment on a video you commented on'),
        ('newsletter', 'Receive an occasional newsletter'),
    )
    ADMIN_CHOICES = (
        ('admin_new_comment', 'A new comment was left on the site'),
        ('admin_new_submission', 'A new video was submitted'),
        ('admin_new_playlist', 'A playlist requested to be public'),
        ('admin_video_updated',
         'The metadata of a video was updated on a remote site'),
        ('admin_queue_daily', 'A daily update of the review queue status'),
        ('admin_queue_weekly', 'A weekly update of the review queue status'),
    )

    notifications = forms.MultipleChoiceField(
        required=False, choices=CHOICES,
        widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        forms.Form.__init__(self, *args, **kwargs)
        if self.instance:
            field = self.fields['notifications']
            sitelocation = SiteLocation.objects.get_current()
            if sitelocation.user_is_admin(self.instance):
                field.choices = self.CHOICES + self.ADMIN_CHOICES

            initial = []
            for choice, label in field.choices:
                notice_type = notification.NoticeType.objects.get(label=choice)
                if notification.should_send(self.instance, notice_type, "1"):
                    initial.append(choice)
            self.initial.setdefault('notifications', initial)


    def save(self):
        if not self.instance:
            raise RuntimeError('Cannot save the notifications without a user.')

        for choice, label in self.fields['notifications'].choices:
            notice_type = notification.NoticeType.objects.get(label=choice)
            setting = notification.get_notification_setting(self.instance,
                                                            notice_type, "1")
            setting.send = choice in self.cleaned_data['notifications']
            setting.save()
        return self.instance
