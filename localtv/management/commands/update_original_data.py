import traceback

from django.core.management.base import NoArgsCommand
from localtv.management import site_too_old
from localtv import models
import vidscraper.errors

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return
        for original in models.OriginalVideo.objects.exclude(
            video__status=models.FEED_STATUS_REJECTED):
            try:
                original.update()
            except vidscraper.errors.CantIdentifyUrl, e:
                pass # It is okay if we cannot update a remote video. No need to be noisy.
            except Exception:
                traceback.print_exc()
