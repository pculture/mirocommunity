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

from localtv.models import SiteLocation


class FixAJAXMiddleware(object):
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

class UserIsAdminMiddleware(object):
    """
    Adds a user_is_admin method to all processed requests. The results of the
    call to SiteLocation.user_is_admin are cached on the request object to
    avoid unnecessary queries.
    
    """
    def process_request(self, request):
        def user_is_admin(request=request):
            if not hasattr(request, '_user_is_admin_cache'):
                sl = SiteLocation.objects.get_current()
                request._user_is_admin_cache = sl.user_is_admin(request.user)
            return request._user_is_admin_cache
        request.user_is_admin = user_is_admin
