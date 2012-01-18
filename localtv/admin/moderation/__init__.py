# Copyright 2010 - Participatory Culture Foundation
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

from django.conf.urls.defaults import url, patterns
from django.utils.translation import ugettext_lazy as _

from localtv.admin.base import MiroCommunityAdminSection, registry
from localtv.admin.moderation.views import (VideoModerationQueueView,
                                            CommentModerationQueueView)


class VideoModerationSection(MiroCommunityAdminSection):
    url_prefix = 'videos'
    navigation_text = _('Videos')
    root_url_name = 'localtv_admin_video_queue'
    site_admin_required = True

    @property
    def urlpatterns(self):
        urlpatterns = patterns('',
            url(
                r'^$',
                self.wrap_view(VideoModerationQueueView.as_view()),
                name='localtv_admin_video_queue'
            )
        )
        return urlpatterns


class CommentModerationSection(MiroCommunityAdminSection):
    url_prefix = 'comments'
    navigation_text = _('Comments')
    root_url_name = 'localtv_admin_comment_queue'
    site_admin_required = True

    @property
    def urlpatterns(self):
        urlpatterns = patterns('',
            url(
                r'^comments/$',
                self.wrap_view(CommentModerationQueueView.as_view()),
                name='localtv_admin_comment_queue'
            )
        )
        return urlpatterns


class ModerationSection(MiroCommunityAdminSection):
    url_prefix = 'moderation'
    navigation_text = _('Moderation')
    root_url_name = 'localtv_admin_video_queue'
    site_admin_required = True
    subsection_classes = (VideoModerationSection, CommentModerationSection)


registry.register(ModerationSection)