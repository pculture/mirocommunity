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

from django.core.management.base import NoArgsCommand
from django.template import Context, loader

from localtv import models
from localtv import util

class Command(NoArgsCommand):

    def handle_noargs(self, **kwargs):
        sitelocation = models.SiteLocation.objects.get_current()

        previous_day = datetime.datetime.now() - datetime.timedelta(hours=24)

        queue_videos = models.Video.objects.filter(
            site=sitelocation.site,
            status=models.VIDEO_STATUS_UNAPPROVED)
        new_videos = queue_videos.filter(when_submitted__gte=previous_day,
                                         feed=None, search=None)
        if new_videos.count():
            subject = 'Video Submissions for %s' % sitelocation.site.name
            t = loader.get_template(
                'localtv/submit_video/review_status_email.txt')
            c = Context({'new_videos': new_videos,
                         'queue_videos': queue_videos,
                         'site': sitelocation.site})
            message = t.render(c)
            util.send_notice('admin_queue_daily',
                             subject, message,
                             sitelocation=sitelocation)
