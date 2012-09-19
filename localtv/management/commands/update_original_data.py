import traceback

from django.core.management.base import NoArgsCommand
from localtv.management import site_too_old
from localtv.models import Video, OriginalVideo
from vidscraper.exceptions import UnhandledVideo

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return
        for original in OriginalVideo.objects.exclude(
            video__status=Video.REJECTED):
            try:
                original.update()
            except UnhandledVideo:
                pass # It is okay if we cannot update a remote video. No need to be noisy.
            except Exception:
                traceback.print_exc()
