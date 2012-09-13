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

