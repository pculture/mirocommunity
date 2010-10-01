import traceback
import datetime

from django.core.management.base import NoArgsCommand
from localtv.management import site_too_old
from localtv import models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return

        # all feeds submitted more than an hour ago should be shown
        hour = datetime.timedelta(hours=1)
        models.Feed.objects.filter(
            when_submitted__lte=datetime.datetime.now()-hour,
            status=models.FEED_STATUS_UNAPPROVED).update(
            status=models.FEED_STATUS_ACTIVE)

        for feed in models.Feed.objects.filter(
            status=models.FEED_STATUS_ACTIVE):
            try:
                feed.update_items()
            except:
                traceback.print_exc()
