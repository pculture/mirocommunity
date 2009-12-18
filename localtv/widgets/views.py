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

import datetime

from django.shortcuts import render_to_response
from django.template.context import RequestContext

from localtv import models
from localtv.decorators import get_sitelocation

def widget(func):
    def wrapper(request, *args, **kwargs):
        objects = func(request, *args, **kwargs)
        try:
            count = int(request.GET.get('count'))
        except TypeError:
            count = 3
        else:
            objects = objects[:count]
        return render_to_response('localtv/widgets/widget.html',
                                  {'objects': objects},
                                  context_instance=RequestContext(request))
    return wrapper

@widget
@get_sitelocation
def featured(request, sitelocation):
    featured_videos = models.Video.objects.filter(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE,
        last_featured__isnull=False)
    featured_videos = featured_videos.order_by(
        '-last_featured', '-when_approved', '-when_published',
        '-when_submitted')
    return featured_videos

@widget
@get_sitelocation
def new(request, sitelocation):
    new_videos = models.Video.objects.new(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)
    return new_videos

@widget
@get_sitelocation
def popular(request, sitelocation):
    popular_videos = models.Video.objects.popular_since(
        datetime.timedelta(days=7), sitelocation=sitelocation,
        status=models.VIDEO_STATUS_ACTIVE)
    return popular_videos
