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

from django.conf import settings
from django.contrib import comments, messages
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.template import loader, Context
from django.template.defaultfilters import pluralize
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _

if 'notification' in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

from localtv.admin.feeds import generate_secret
from localtv.admin.moderation.forms import (RequestModerationFormSet,
                                            CommentModerationForm,
                                            VideoModerationForm,
                                            VideoLimitFormSet)
from localtv.admin.views import MiroCommunityAdminListView
from localtv.models import Video


class ModerationQueueView(MiroCommunityAdminListView):
    def formset_valid(self, formset):
        response = super(ModerationQueueView, self).formset_valid(formset)

        for action, count in formset._action_counts.iteritems():
            if count > 0:
                if count > 1:
                    model_text = formset.model._meta.verbose_name_plural
                else:
                    model_text = formset.model._meta.verbose_name
                messages.add_message(
                    self.request,
                    messages.SUCCESS,
                    _(u"%s %d %s" % (self.get_action_text(action),
                                    count, model_text))
                )
        return response

    def get_action_text(self, action):
        if action == self.form_class.APPROVE:
            return "Approved"
        if action == self.form_class.REJECT:
            return "Rejected"
        return "Unknown action taken with"


class VideoModerationQueueView(ModerationQueueView):
    form_class = VideoModerationForm
    formset_class = VideoLimitFormSet
    paginate_by = 10
    context_object_name = 'videos'
    template_name = 'localtv/admin/moderation/videos/queue.html'

    def get_queryset(self):
        return Video.objects.filter(
            status=Video.UNAPPROVED,
            site=Site.objects.get_current()
        ).order_by('when_submitted', 'when_published')

    def get_context_data(self, **kwargs):
        context = super(VideoModerationQueueView, self).get_context_data(**kwargs)
        try:
            current_video = context['object_list'][0]
        except IndexError:
            current_video = None
        
        context.update({
            'feed_secret': generate_secret(),
            'current_video': current_video
        })
        return context

    def get_action_text(self, action):
        if action == self.form_class.FEATURE:
            return "Featured"
        return super(VideoModerationQueueView, self).get_action_text(action)

    def formset_valid(self, formset):
        response = super(VideoModerationQueueView, self).formset_valid(formset)

        approved_count = (formset._action_counts[formset.form.APPROVE] +
                          formset._action_counts[formset.form.FEATURE])
        if notification and approved_count > 0:
            notice_type = notification.NoticeType.objects.get(
                                                        label="video_approved")
            t = loader.get_template(
                        'localtv/submit_video/approval_notification_email.txt')
            for instance in self.object_list:
                if (instance.status == Video.ACTIVE and
                    instance.user is not None and instance.user.email and
                    notification.should_send(instance.user, notice_type, "1")):
                    c = Context({
                        'current_video': instance
                    })
                    subject = '[%s] "%s" was approved!' % (instance.site.name,
                                                           instance.name)
                    body = t.render(c)
                    EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL,
                                [instance.user.email]).send(fail_silently=True)

        return response


class CommentModerationQueueView(ModerationQueueView):
    formset_class = RequestModerationFormSet
    form_class = CommentModerationForm
    paginate_by = 10
    context_object_name = 'comments'
    template_name = 'localtv/admin/moderation/comments/queue.html'
    queryset = comments.get_model()._default_manager.filter(is_public=False,
                                                            is_removed=False)

    def get_formset_kwargs(self, queryset=None):
        kwargs = super(CommentModerationQueueView, self).get_formset_kwargs(
                                                            queryset=queryset)
        kwargs['request'] = self.request
        return kwargs
