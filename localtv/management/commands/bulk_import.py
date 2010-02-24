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
        try:
            verbose = (int(options['verbosity']) > 1)
        except ValueError:
            verbose = False

        for i in feed._update_items_generator(verbose=verbose,
                                              parsed_feed=bulk_feed,
                                              clear_rejected=True):
            if not models.Feed.objects.filter(pk=feed.pk).count():
                # someone deleted the feed, quit
                print 0
                return
        print feed.video_set.count()
