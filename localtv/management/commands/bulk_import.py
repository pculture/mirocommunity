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

from django.core.management.base import BaseCommand, CommandError
from django.utils import simplejson

from localtv import models


class Command(BaseCommand):

    args = '[feed primary key]'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('bulk_import takes one argument: '
                               '%i argument(s) given' % len(args))
        try:
            feed = models.Feed.objects.get(pk=args[0])
        except models.Feed.DoesNotExist:
            raise CommandError('Feed with pk %s does not exist' % args[0])

        try:
            self.verbose = (int(options['verbosity']) > 1)
        except (KeyError, ValueError):
            self.verbose = False

        stats = {
            'total': 0,
            'imported': 0,
            'skipped': 0
            }
        try:
            for i in feed._update_items_generator(
                verbose=self.verbose,
                clear_rejected=True,
                actually_save_thumbnails=True,
                max_results=100,
                crawl=True):
                if not models.Feed.objects.filter(pk=feed.pk).exists():
                    # someone deleted the feed, quit
                    break
                stats['total'] += 1
                if i['video'] is not None:
                    stats['imported'] += 1
                else:
                    stats['skipped'] += 1
        finally:
            feed.status = models.Feed.ACTIVE
            feed.save()
        print simplejson.dumps(stats),
