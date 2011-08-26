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

from localtv.models import Video


def widget(func):
    def wrapper(request, *args, **kwargs):
        objects = func(*args, **kwargs)
        try:
            count = int(request.GET.get('count'))
        except TypeError:
            count = 3

        objects = objects[:count]
        return render_to_response('localtv/widgets/widget.html',
                                  {'objects': objects},
                                  context_instance=RequestContext(request))
    return wrapper


featured = widget(Video.objects.get_featured_videos)
new = widget(Video.objects.get_latest_videos)
popular = widget(Video.objects.get_popular_videos)
