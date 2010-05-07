import traceback

from django.core.management.base import NoArgsCommand
from localtv.management import site_too_old
from localtv import models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return
        for feed in models.Feed.objects.filter(
            status=models.FEED_STATUS_ACTIVE):
            try:
                feed.update_items()
            except:
                traceback.print_exc()
