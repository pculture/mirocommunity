import traceback

from django.core.files.storage import default_storage
from django.core.management.base import NoArgsCommand
from django.db.models import Q

from localtv.management import site_too_old
from localtv import models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, verbosity=0, **options):
        if site_too_old():
            return
        has_thumbnail = Q(has_thumbnail=True)
        has_thumbnail_url = ~Q(thumbnail_url='')
        for v in models.Video.objects.filter(has_thumbnail |
                                             has_thumbnail_url):
            path = v.get_original_thumb_storage_path()
            if not default_storage.exists(path):
                if verbosity >= 1:
                    print 'saving', v, '(%i)' % v.pk
                try:
                    # resave the thumbnail
                    v.save_thumbnail()
                except Exception:
                    traceback.print_exc()

