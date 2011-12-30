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

from django.conf.urls.defaults import patterns, url

from localtv.decorators import request_passes_test
from localtv.submit_video.views import (SubmitURLView, SubmitVideoView,
                                        submit_thanks, _has_submit_permissions)


request_has_submit_permissions = request_passes_test(_has_submit_permissions)
submit_video = request_has_submit_permissions(SubmitVideoView.as_view())
urlpatterns = patterns('',
    url(r'^$', request_has_submit_permissions(SubmitURLView.as_view()),
    	name='localtv_submit_video'),
    url(r'^scraped/$', submit_video, name='localtv_submit_scraped_video'),
    url(r'^embed/$', submit_video, name='localtv_submit_embedrequest_video'),
    url(r'^directlink/$', submit_video, name='localtv_submit_directlink_video'),
    url(r'^thanks/(?P<video_id>\d+)?$', submit_thanks,
        name='localtv_submit_thanks')
)
