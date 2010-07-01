# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
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

import urlparse

from django.conf import settings

from localtv import models

class FixAJAXMiddleware:
    """
    Firefox doesn't handle redirects in XMLHttpRequests correctly (it doesn't
    set X-Requested-With) so we fake it with a GET argument.
    """
    def process_request(self, request):
        if 'from_ajax' in request.GET and not request.is_ajax():
            request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

    def process_response(self, request, response):
        if 300 <= response.status_code < 400 and request.is_ajax():
            parts = list(urlparse.urlparse(response['Location']))
            if parts[4]: # query
                parts[4] = parts[4] + '&from_ajax'
            else:
                parts[4] = 'from_ajax'
            response['Location'] = urlparse.urlunparse(parts)
        return response

def context_processor(request):
    sitelocation = models.SiteLocation.objects.get_current()

    display_submit_button = sitelocation.display_submit_button
    if display_submit_button:
        if request.user.is_anonymous() and \
                sitelocation.submission_requires_login:
            display_submit_button = False
    else:
        if sitelocation.user_is_admin(request.user):
            display_submit_button = True

    try:
        cache_invalidator = str(models.Video.objects.order_by(
                '-when_modified').values_list('when_modified', flat=True)[0])
    except IndexError:
        cache_invalidator = None

    return  {
        'sitelocation': sitelocation,
        'request': request,
        'user_is_admin': sitelocation.user_is_admin(request.user),
        'categories':  models.Category.objects.filter(site=sitelocation.site,
                                                      parent=None),
        'cache_invalidator': cache_invalidator,

        'display_submit_button': display_submit_button,

        'settings': settings,

        'VIDEO_STATUS_UNAPPROVED': models.VIDEO_STATUS_UNAPPROVED,
        'VIDEO_STATUS_ACTIVE': models.VIDEO_STATUS_ACTIVE,
        'VIDEO_STATUS_REJECTED': models.VIDEO_STATUS_REJECTED}
