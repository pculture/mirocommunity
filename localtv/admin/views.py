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
import math

from django.contrib import comments
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv.decorators import require_site_admin
from localtv import models
import localtv.tiers

@require_site_admin
def index(request):
    """
    Simple index page for the admin site.
    """
    total_count = localtv.tiers.current_videos_that_count_toward_limit().count()
    percent_videos_used = math.floor(
        (100.0 * total_count) / request.sitelocation.get_tier().videos_limit())
    return render_to_response(
        'localtv/admin/index.html',
        {'total_count': total_count,
         'percent_videos_used': percent_videos_used,
         'unreviewed_count': models.Video.objects.filter(
                site=request.sitelocation.site,
                status=models.VIDEO_STATUS_UNAPPROVED).count(),
         'comment_count': comments.get_model().objects.filter(
                is_public=False, is_removed=False).count()},
        context_instance=RequestContext(request))
