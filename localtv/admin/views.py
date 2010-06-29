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
from django.contrib import comments
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv import models

@require_site_admin
@get_sitelocation
def index(request, sitelocation=None):
    """
    Simple index page for the admin site.
    """
    return render_to_response(
        'localtv/admin/index.html',
        {'total_count': models.Video.objects.filter(
                site=sitelocation.site,
                status=models.VIDEO_STATUS_ACTIVE).count(),
         'unreviewed_count': models.Video.objects.filter(
                site=sitelocation.site,
                status=models.VIDEO_STATUS_UNAPPROVED).count(),
         'comment_count': comments.get_model().objects.filter(
                is_public=False, is_removed=False).count()},
        context_instance=RequestContext(request))
