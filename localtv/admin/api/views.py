# Copyright 2010 - Participatory Culture Foundation
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

# This file temporarily holds all "api-like" views until they can be converted
# to use tastypie.

from django.http import HttpResponse, HttpResponseBadRequest

from localtv.decorators import require_site_admin
from localtv.models import SiteLocation

@require_site_admin
def hide_get_started(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('You have to POST to this URL.')
    site_location = SiteLocation.objects.get_current()
    site_location.hide_get_started = True
    site_location.save()
    return HttpResponse("OK")
    
