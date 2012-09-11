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

from django.conf.urls.defaults import patterns

from localtv import models


urlpatterns = patterns(
    'localtv.inline_edit',
    (r'^video/(?P<id>[0-9]+)/name/$', 'simple.edit_field',
     {'model': models.Video, 'field': 'name'},
     'localtv_admin_video_edit_name'),
    (r'^video/(?P<id>[0-9]+)/when_published/$', 'simple.edit_field',
     {'model': models.Video, 'field': 'when_published'},
     'localtv_admin_video_edit_when_published'),
    (r'^video/(?P<id>[0-9]+)/authors/$', 'simple.edit_field',
     {'model': models.Video, 'field': 'authors'},
     'localtv_admin_video_edit_authors'),
    (r'^video/(?P<id>[0-9]+)/categories/$', 'simple.edit_field',
    {'model': models.Video, 'field': 'categories'},
     'localtv_admin_video_edit_categories'),
    (r'^video/(?P<id>[0-9]+)/tags/$', 'simple.edit_field',
    {'model': models.Video, 'field': 'tags'},
     'localtv_admin_video_edit_tags'),
    (r'^video/(?P<id>[0-9]+)/description/$', 'simple.edit_field',
     {'model': models.Video, 'field': 'description'},
     'localtv_admin_video_edit_description'),
    (r'^video/(?P<id>[0-9]+)/website_url/$', 'simple.edit_field',
     {'model': models.Video, 'field': 'website_url'},
     'localtv_admin_video_edit_website_url'),
    (r'^video/(?P<id>[0-9]+)/editors_comment/$', 'video_views.editors_comment',
     {}, 'localtv_admin_video_edit_editors_comment'),
    (r'^video/(?P<id>[0-9]+)/thumbnail/$', 'simple.edit_field',
     {'model': models.Video, 'field': 'thumbnail'},
     'localtv_admin_video_edit_thumbnail'),
    (r'^playlist/([0-9]+)/info/$', 'playlist.info',
     {}, 'localtv_admin_playlist_edit_info'),
    )
