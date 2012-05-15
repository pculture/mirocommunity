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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

import os

from django.conf import settings

from localtv.models import SiteSettings, Video, Category
from localtv.settings import ENABLE_CHANGE_STAMPS


def localtv(request):
    site_settings = SiteSettings.objects.get_current()

    display_submit_button = site_settings.display_submit_button
    if display_submit_button:
        if request.user.is_anonymous() and \
                site_settings.submission_requires_login:
            display_submit_button = False
    else:
        if request.user_is_admin():
            display_submit_button = True

    if ENABLE_CHANGE_STAMPS:
        try:
            cache_invalidator = os.stat(
                os.path.join(settings.MEDIA_ROOT,
                             '.video-published-stamp')).st_mtime
        except OSError:
            cache_invalidator = None
    else:
        try:
            cache_invalidator = str(Video.objects.order_by(
                    '-when_modified').values_list(
                    'when_modified', flat=True)[0])
        except IndexError:
            cache_invalidator = None

    return  {
        'mc_version': '1.2',
        'site_settings': site_settings,
        # Backwards-compatible for custom themes.
        'sitelocation': site_settings,
        'user_is_admin': request.user_is_admin(),
        'categories':  Category.objects._mptt_filter(site=site_settings.site,
                                                     parent__isnull=True),
        'cache_invalidator': cache_invalidator,

        'display_submit_button': display_submit_button,

        'settings': settings,

        'VIDEO_STATUS_UNAPPROVED': Video.UNAPPROVED,
        'VIDEO_STATUS_ACTIVE': Video.ACTIVE,
        'VIDEO_STATUS_REJECTED': Video.REJECTED}
