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

from django.contrib.auth.decorators import user_passes_test
from django.http import Http404, HttpResponse
from django.contrib.sites.models import Site

from localtv.models import SiteLocation

@user_passes_test(lambda u: u.is_staff)
def create_site(request):
    if request.method != 'POST':
        raise Http404
    site_name = request.POST.get('site_name')
    if site_name is None:
        return HttpResponse('please include a site name')
    full_name = site_name + '.mirocommunity.org'
    if Site.objects.filter(domain=full_name).count():
        return HttpResponse('that domain already exists')
    site = Site(domain=full_name, name=site_name)
    site.save()
    site_location = SiteLocation(site=site)
    site_location.save()
    return HttpResponse('%s created.  Ask someone to set up a new Django project with SITE_ID=%i' % (
            full_name, site.id))
