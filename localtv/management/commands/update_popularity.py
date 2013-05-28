from datetime import datetime, timedelta
from optparse import make_option

from django.core.management.base import LabelCommand

from localtv.management import site_too_old
from localtv.models import Video


class Command(LabelCommand):
    option_list = (
        make_option('--since', action='store', dest='since', default=11,
                    type='int', help='The number of days in the past for which all watched videos should be reindexed.'),
    ) + LabelCommand.option_list

    def handle(self, **options):
        if site_too_old():
            return

        since = options['since']
        from localtv.tasks import haystack_batch_update

        haystack_batch_update.delay(Video._meta.app_label,
                                    Video._meta.module_name,
                                    start=datetime.now() - timedelta(since),
                                    date_lookup='watch__timestamp')
