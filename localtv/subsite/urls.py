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

from django.conf.urls.defaults import patterns, include
from django.conf import settings

urlpatterns = patterns(
    'localtv.subsite.views',
    (r'^$', 'subsite_index', {}, 'localtv_subsite_index'),
    (r'^about/$', 'about', {}, 'localtv_about'),
    (r'^search/$', 'video_search', {}, 'localtv_subsite_search'),
    (r'^category/$', 'category', {}, 'localtv_subsite_category_index'),
    (r'^category/([-\w]+)$', 'category', {}, 'localtv_subsite_category'),
    (r'^author/$', 'author', {}, 'localtv_subsite_author_index'),
    (r'^author/(\d+)$', 'author', {}, 'localtv_subsite_author'),
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^video/(?P<video_id>[0-9]+)/(?P<slug>[\w-]*)$', 'view_video',
     {}, 'localtv_view_video'))

urlpatterns += patterns(
    '',
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout', {
            'next_page': '/'}),
    (r'^accounts/', include('django.contrib.auth.urls')),
    (r'^openid/', include('localtv.openid.urls')),
    (r'^admin/edit_attributes/', include('localtv.inline_edit.urls')),
    (r'^admin/', include('localtv.admin.urls')),
    (r'^submit_video/', include('localtv.submit_video.urls')),
    (r'^listing/', include('localtv.subsite.listing.urls')),
    (r'^feeds/', include('localtv.subsite.feeds.urls')))

if settings.DEBUG:
    # show the thumbnails/logo etc, without relying on Apache
    urlpatterns += patterns('',
                            (r'^localtv/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'localtv'}),
                            )
