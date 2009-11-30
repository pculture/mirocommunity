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

from django.contrib.auth.models import User
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic.list_detail import object_list

from localtv import models
from localtv.decorators import get_sitelocation

@get_sitelocation
def index(request, sitelocation=None):
    return render_to_response(
        'localtv/subsite/browse.html', {},
        context_instance=RequestContext(request))


@get_sitelocation
def new_videos(request, sitelocation=None):
    videos = models.Video.objects.new(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)
    return object_list(
        request=request, queryset=videos,
        paginate_by=15,
        template_name='localtv/subsite/video_listing_new.html',
        allow_empty=True, template_object_name='video')


@get_sitelocation
def popular_videos(request, sitelocation=None):
    videos = models.Video.objects.popular_since(
        datetime.timedelta(days=7), sitelocation,
        status=models.VIDEO_STATUS_ACTIVE)
    return object_list(
        request=request, queryset=videos,
        paginate_by=15,
        template_name='localtv/subsite/video_listing_popular.html',
        allow_empty=True, template_object_name='video')

@get_sitelocation
def featured_videos(request, sitelocation=None):
    videos = models.Video.objects.filter(
        site=sitelocation.site, last_featured__isnull=False,
        status=models.VIDEO_STATUS_ACTIVE)
    videos = videos.order_by(
        '-last_featured', '-when_approved', '-when_published',
        '-when_submitted')
    return object_list(
        request=request, queryset=videos,
        paginate_by=15,
        template_name='localtv/subsite/video_listing_featured.html',
        allow_empty=True, template_object_name='video')

@get_sitelocation
def tag_videos(request, tag, sitelocation=None):
    tag = get_object_or_404(models.Tag, name=tag)
    videos = tag.video_set.filter(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)
    videos = videos.order_by(
        '-when_approved', '-when_published', '-when_submitted')
    return object_list(
        request=request, queryset=videos,
        paginate_by=15,
        template_name='localtv/subsite/video_listing_tag.html',
        allow_empty=True, template_object_name='video',
        extra_context={'tag': tag})

@get_sitelocation
def feed_videos(request, feed_id, sitelocation=None):
    feed = get_object_or_404(models.Feed, pk=feed_id,
                             site=sitelocation.site)
    videos = models.Video.objects.new(site=sitelocation.site,
                                      feed=feed,
                                      status=models.VIDEO_STATUS_ACTIVE)
    return object_list(
        request=request, queryset=videos,
        paginate_by=15,
        template_name='localtv/subsite/video_listing_feed.html',
        allow_empty=True, template_object_name='video',
        extra_context={'feed': feed})
