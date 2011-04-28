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

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from localtv import models
import localtv.util

class Command(BaseCommand):

    args = '[video primary key]'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError('update_one_thumbnail takes two arguments: '
                               '%i argument(s) given' % len(args))
        try:
            video = models.Video.objects.get(pk=args[0])
            future_status = int(args[1])
        except models.Feed.DoesNotExist:
            raise CommandError('Video with pk %s does not exist' % args[0])
        self.actually_update_thumb(video, future_status)

    def actually_update_thumb(self, video, future_status):
        thumbnail_data = None
        if video.thumbnail_url:
            try:
                thumbnail_data = localtv.util.pull_downloaded_file_from_cache(video.thumbnail_url)
            except IOError:
                pass # Aw well, we can't have nice things.

        if thumbnail_data is not None:
            # wrap it in a Django ContentFile, and pass it through.
            cf_image = ContentFile(thumbnail_data)
            video.save_thumbnail_from_file(cf_image)
        else:
            video.save_thumbnail()

        # Set the status.
        # However, if the video wants to become ACTIVE but we may not make it
        # ACTIVE, make it UNAPPROVED instead.
        if future_status == models.VIDEO_STATUS_ACTIVE:
            if not models.SiteLocation.objects.get().get_tier().can_add_more_videos():
                future_status = models.VIDEO_STATUS_UNAPPROVED

        video.status = future_status
        video.save()
