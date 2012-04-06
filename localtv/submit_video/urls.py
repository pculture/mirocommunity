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

from django.conf.urls.defaults import patterns, url

from localtv.submit_video import views

urlpatterns = patterns('',
    url(r'^$', views.can_submit_video(views.SubmitURLView.as_view()),
    	name='localtv_submit_video'),
    url(r'^scraped/$', views.can_submit_video(
            views.ScrapedSubmitVideoView.as_view()),
        name='localtv_submit_scraped_video'),
    url(r'^embed/$', views.can_submit_video(
            views.EmbedSubmitVideoView.as_view()),
        name='localtv_submit_embedrequest_video'),
    url(r'^directlink/$', views.can_submit_video(
            views.DirectLinkSubmitVideoView.as_view()),
        name='localtv_submit_directlink_video'),
    url(r'^thanks/(?P<video_id>\d+)?$', views.submit_thanks,
        name='localtv_submit_thanks')
)
