import sys
import traceback

from django.core.files.storage import default_storage
from django.core.management.base import NoArgsCommand

from localtv.management import site_too_old
from localtv import models
from localtv.tasks import video_save_thumbnail

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, verbosity=0, **options):
        if site_too_old():
            return
        for v in models.Video.objects.exclude(thumbnail_url=''):
            if (not v.thumbnail or
                not default_storage.exists(v.thumbnail.name)):
                if verbosity >= 1:
                    print >> sys.stderr, 'saving', repr(v), '(%i)' % v.pk
                try:
                    # resave the thumbnail
                    video_save_thumbnail.apply(args=(v.pk,))
                except Exception:
                    traceback.print_exc()

