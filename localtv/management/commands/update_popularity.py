# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
#
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community. If not, see <http://www.gnu.org/licenses/>.

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
        from localtv.tasks import haystack_batch_update, CELERY_USING

        haystack_batch_update.delay(Video._meta.app_label,
                                    Video._meta.module_name,
                                    start=datetime.now() - timedelta(since),
                                    date_lookup='watch__timestamp',
                                    using=CELERY_USING)
