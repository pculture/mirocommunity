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

import datetime

from django.contrib import comments
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseBadRequest

from localtv.decorators import require_site_admin
from localtv.models import Video, SiteSettings

@require_site_admin
def index(request):
    """
    Simple index page for the admin site.
    """
    site_settings = SiteSettings.objects.get_current()
    total_count = Video.objects.filter(
        status=Video.ACTIVE,
        site=site_settings.site).count()
    videos_this_week_count = Video.objects.filter(
        status=Video.ACTIVE,
        when_approved__gt=(datetime.datetime.utcnow() - datetime.timedelta(days=7))
        ).count()
    return render_to_response(
        'localtv/admin/index.html',
        {'total_count': total_count,
         'unreviewed_count': Video.objects.filter(
                status=Video.UNAPPROVED,
                site=site_settings.site).count(),
         'videos_this_week_count': videos_this_week_count,
         'comment_count': comments.get_model().objects.filter(
                is_public=False, is_removed=False).count()},
        context_instance=RequestContext(request))

@require_site_admin
def hide_get_started(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('You have to POST to this URL.')
    site_settings = SiteSettings.objects.get_current()
    site_settings.hide_get_started = True
    site_settings.save()
    return HttpResponse("OK")
    
