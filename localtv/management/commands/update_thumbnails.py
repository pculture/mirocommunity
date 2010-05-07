import traceback

from django.core.files.storage import default_storage
from django.core.management.base import NoArgsCommand

from localtv.management import site_too_old
from localtv import models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return
        for v in models.Video.objects.filter(has_thumbnail=True):
            path = v.get_original_thumb_storage_path()
            if not default_storage.exists(path):
                try:
                    # resave the thumbnail
                    v.save_thumbnail()
                except Exception:
                    traceback.print_exc()

