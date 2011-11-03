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

#import eventlet
#eventlet.monkey_patch()

from django.core.management.base import BaseCommand, CommandError
from django.utils import simplejson

from optparse import make_option

from localtv import models
from localtv import tiers

import vidscraper

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--crawl',
                    action='store_true',
                    dest='crawl',
                    default=False,
                    help=('Crawl the entire feed (if possible), rather than '
                          'just the first page')),
        )
    args = '[feed primary key]'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('bulk_import takes one argument: '
                               '%i argument(s) given' % len(args))

        if models.SiteLocation.enforce_tiers():
            max_results = 1000
        else:
            tier = tiers.Tier.get()
            max_results = tier.remaining_videos()

        try:
            feed = models.Feed.objects.get(pk=args[0])
        except models.Feed.DoesNotExist:
            raise CommandError('Feed with pk %s does not exist' % args[0])

        try:
            self.verbose = (int(options['verbosity']) > 1)
        except (KeyError, ValueError):
            self.verbose = False

        video_iter = vidscraper.auto_feed(
            feed.feed_url, crawl=options['crawl'],
            max_results=max_results)
        from localtv import tasks
        video_iter = tasks.vidscraper_load.delay(video_iter).get()
        if self.verbose:
            print 'Loaded object:', repr(video_iter)
            print 'Loaded feed:', video_iter.title
        stats = {
            'total': video_iter.entry_count,
            }
        if self.verbose:
            print 'Entry count:', video_iter.entry_count
        try:
            imported = feed.update_items(
                verbose=self.verbose,
                clear_rejected=True,
                video_iter=video_iter)
            print 'Imported videos:', imported
        finally:
            feed.status = models.Feed.ACTIVE
            feed.save()
        stats['imported'] = imported
        stats['skipped'] = max_results - imported
        print simplejson.dumps(stats),
