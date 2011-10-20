# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2011, 2012 Participatory Culture Foundation
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

from django.conf.urls.defaults import patterns, include, url


urlpatterns = patterns('localtv.contrib.contest.views',
    url(r'^contest/vote/(?P<object_id>\d+)/(?P<direction>up|clear)/$',
        'video_vote_view', {
            'template_object_name': 'video',
            'template_name': 'contest/video_vote_confirm.html',
            'allow_xmlhttprequest': False,
        }, 'contest_video_vote'
    ),
    url(r'^admin/categories/votes/([-\w]+)$', 'votes',
        name='localtv_admin_category_votes'
    )
)
