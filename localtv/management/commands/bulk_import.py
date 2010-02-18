from django.core.management.base import BaseCommand, CommandError
from vidscraper.bulk_import import bulk_import

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

        bulk_feed = bulk_import(feed.feed_url)
        feed.update_items(verbose=(options['verbosity']>1),
                          parsed_feed=bulk_feed, clear_rejected=True)
        print feed.video_set.count()
