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

from django.core.management.base import NoArgsCommand

from localtv.management import site_too_old
from localtv.models import Video


class Command(NoArgsCommand):
    def handle_noargs(self, verbosity=0, **options):
        if site_too_old():
            return

        from localtv.tasks import haystack_batch_update, CELERY_USING

        haystack_batch_update.delay(Video._meta.app_label,
                                    Video._meta.module_name,
                                    start=datetime.now() - timedelta(11),
                                    date_lookup='watch__timestamp',
                                    using=CELERY_USING)
