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

from optparse import make_option

from django.conf import settings

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
        from localtv import models, tasks

        if len(args) != 1:
            raise CommandError('bulk_import takes one argument: '
                               '%i argument(s) given' % len(args))

        try:
            feed = models.Feed.objects.get(pk=args[0])
        except models.Feed.DoesNotExist:
            raise CommandError('Feed with pk %s does not exist' % args[0])

        tasks.bulk_import.delay(feed.pk, crawl=options.get('crawl', False),
                                using=settings.SETTINGS_MODULE.split('.')[0])
