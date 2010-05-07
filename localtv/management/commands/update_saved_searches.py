import traceback

from django.core.management.base import NoArgsCommand

from localtv.management import site_too_old
from localtv import models

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return
        for saved_search in models.SavedSearch.objects.all():
            try:
                saved_search.update_items()
            except:
                traceback.print_exc()
