# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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
import logging

from django.core.management.base import NoArgsCommand
from localtv.management import site_too_old
from localtv import models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return
        newsletter = models.NewsletterSettings.objects.get_current()
        if not newsletter.repeat:
            return
        if not newsletter.sitelocation.get_tier().permit_newsletter():
            return

        now = datetime.datetime.now()
        if now > newsletter.next_send_time():
            logging.warning('Sending newsletter for %s',
                            newsletter.sitelocation.site.domain)
            newsletter.send()
            # we increment by the repeat so that last_sent maintains the
            # weekday and hour that the user has assigned
            repeat = datetime.timedelta(hours=newsletter.repeat)
            while newsletter.next_send_time() < now:
                newsletter.last_sent += repeat
            newsletter.save()
            logging.warning('Next send scheduled for %s',
                            newsletter.next_send_time())
