# Miro Community
# Copyright 2009 - Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from django.contrib.sites.models import Site

from localtv import models


def context_processor(request):
    sitelocation = models.SiteLocation.objects.get(
            site=Site.objects.get_current())

    display_submit_button = sitelocation.display_submit_button
    if display_submit_button:
        if request.user.is_anonymous() and \
                sitelocation.submission_requires_login:
            display_submit_button = False
    else:
        if sitelocation.user_is_admin(request.user):
            display_submit_button = True

    return  {
        'sitelocation': sitelocation,
        'request': request,
        'user_is_admin': sitelocation.user_is_admin(request.user),

        'display_submit_button': display_submit_button,

        'settings': settings,

        'VIDEO_STATUS_UNAPPROVED': models.VIDEO_STATUS_UNAPPROVED,
        'VIDEO_STATUS_ACTIVE': models.VIDEO_STATUS_ACTIVE,
        'VIDEO_STATUS_REJECTED': models.VIDEO_STATUS_REJECTED}
