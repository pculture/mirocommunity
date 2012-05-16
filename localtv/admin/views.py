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

from django.conf import settings
from django.contrib import comments
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.generic import TemplateView

from localtv.decorators import require_site_admin
from localtv.models import Video, SiteSettings


class IndexView(TemplateView):
    template_name = 'localtv/admin/index.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        site_videos = Video.objects.filter(site=settings.SITE_ID)
        active_site_videos = site_videos.filter(status=Video.ACTIVE)
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        context.update({
            'total_count': active_site_videos.count(),
            'videos_this_week_count': active_site_videos.filter(
                             when_approved__gt=week_ago).count(),
            'unreviewed_count': site_videos.filter(status=Video.UNAPPROVED
                                          ).count(),
            'comment_count': comments.get_model().objects.filter(
                                                              is_public=False,
                                                              is_removed=False
                                                        ).count()
        })
        return context


index = require_site_admin(IndexView.as_view())


@require_site_admin
def hide_get_started(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('You have to POST to this URL.')
    site_settings = SiteSettings.objects.get_current()
    site_settings.hide_get_started = True
    site_settings.save()
    return HttpResponse("OK")
    
