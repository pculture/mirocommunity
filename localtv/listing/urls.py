# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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

from django.conf.urls.defaults import patterns, url
from django.views.generic.base import TemplateView

from localtv.listing.views import VideoSearchView


urlpatterns = patterns(
    'localtv.listing.views',
    url(r'^$', TemplateView.as_view(template_name="localtv/browse.html"),
                name='localtv_list_index'),
    url(r'^new/$', VideoSearchView.as_view(
                    template_name='localtv/video_listing_new.html',
                    default_sort='-date'
                ), name='localtv_list_new'),
    url(r'^this-week/$', VideoSearchView.as_view(
                    template_name='localtv/video_listing_new.html',
                    approved_since=datetime.timedelta(days=7),
                    default_sort='-approved'
                ), name='localtv_list_this_week'),
    url(r'^popular/$', VideoSearchView.as_view(
                    template_name='localtv/video_listing_popular.html',
                    default_sort='-popular'
                ), name='localtv_list_popular'),
    url(r'^featured/$', VideoSearchView.as_view(
                    template_name='localtv/video_listing_featured.html',
                    default_sort='-featured'
                ), name='localtv_list_featured'),
    url(r'^tag/(?P<name>.+)/$', VideoSearchView.as_view(
                    template_name='localtv/video_listing_tag.html',
                    url_filter='tag',
                    url_filter_kwarg='name',
                    default_sort='-date'
                ), name='localtv_list_tag'),
    url(r'^feed/(?P<pk>\d+)/?$', VideoSearchView.as_view(
                    template_name='localtv/video_listing_feed.html',
                    url_filter='feed',
                    default_sort='-date'
                ), name='localtv_list_feed')
)
