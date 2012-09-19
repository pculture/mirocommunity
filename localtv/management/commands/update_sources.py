from django.core.management.base import NoArgsCommand
from localtv.management import site_too_old


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        if site_too_old():
            return

        from localtv.tasks import update_sources, CELERY_USING
        
        update_sources.delay(using=CELERY_USING)
