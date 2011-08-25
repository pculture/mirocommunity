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
        self.send_email(datetime.timedelta(hours=24),
                        'today',
                        'admin_queue_daily')
        if datetime.date.today().weekday == 0: # Monday
            self.send_email(
                datetime.timedelta(days=7),
                'last week',
                'admin_queue_weekly')

    def send_email(self, delta, time_period, notice_type):
        sitelocation = models.SiteLocation.objects.get_current()

        previous = datetime.datetime.now() - delta

        queue_videos = models.Video.objects.unapproved().filter(
            site=sitelocation.site,
        )
        new_videos = queue_videos.filter(when_submitted__gte=previous)

        if new_videos.count():
            subject = 'Video Submissions for %s' % sitelocation.site.name
            t = loader.get_template(
                'localtv/submit_video/review_status_email.txt')
            c = Context({'new_videos': new_videos,
                         'queue_videos': queue_videos,
                         'time_period': time_period,
                         'site': sitelocation.site})
            message = t.render(c)
            util.send_notice(notice_type,
                             subject, message,
                             sitelocation=sitelocation)
