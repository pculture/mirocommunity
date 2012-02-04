# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

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

