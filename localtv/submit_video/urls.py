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

from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.submit_video.views',
    (r'^$', 'submit_video', {}, 'localtv_submit_video'),
    (r'^scraped/$', 'scraped_submit_video',
     {}, 'localtv_submit_scraped_video'),
    (r'^embed/$', 'embedrequest_submit_video',
     {}, 'localtv_submit_embedrequest_video'),
    (r'^directlink/$', 'directlink_submit_video',
     {}, 'localtv_submit_directlink_video'),
    (r'^thanks/$', 'submit_thanks', {}, 'localtv_submit_thanks'))
