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

from django.core.management.base import NoArgsCommand

import vidscraper

from localtv.management import site_too_old
from localtv import models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return
        for v in models.Video.objects.filter(when_published__isnull=True):
            try:
                video = vidscraper.auto_scrape(v.website_url, fields=[
                        'publish_datetime'])
            except:
                pass
            else:
                if video:
                    v.when_published = video.publish_datetime
                    v.save()

        # Finally, at the end, if stamps are enabled, update them.
        if models.ENABLE_CHANGE_STAMPS:
            models.create_or_delete_video_needs_published_date_stamp()
