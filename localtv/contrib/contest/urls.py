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

from localtv.contrib.contest.views import ContestVoteView


urlpatterns = patterns('localtv.contrib.voting.views',
    url(r'^contest/vote/(?P<category_slug>[\w-])/(?P<video_pk>\d+)/'
        r'(?P<direction>up|clear)/$', ContestVoteView.as_view(),
        name='localtv_contest_vote'),
    url(r'^admin/contest/$', 'contest_admin', name='localtv_admin_contest'),
)
