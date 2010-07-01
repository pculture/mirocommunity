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

urlpatterns = patterns(
    'localtv.views',
    (r'^$', 'index', {}, 'localtv_index'),
    (r'^about/$', 'about', {}, 'localtv_about'),
    (r'^share/(\d+)/(\d+)', 'share_email', {}, 'email-share'),
    (r'^video/(?P<video_id>[0-9]+)/(?P<slug>[\w-]*)/?$', 'view_video',
     {}, 'localtv_view_video'))

urlpatterns += patterns(
    'localtv.listing.views',
    (r'^search/$', 'video_search', {}, 'localtv_search'),
    (r'^category/$', 'category', {}, 'localtv_category_index'),
    (r'^category/([-\w]+)$', 'category', {}, 'localtv_category'),
    (r'^author/$', 'author', {}, 'localtv_author_index'),
    (r'^author/(\d+)$', 'author', {}, 'localtv_author'))

urlpatterns += patterns(
    'localtv.comments.views',
    (r'^comments/post/$', 'post_comment', {}, 'comments-post-comment'),
    (r'^comments/moderation-queue$', 'moderation_queue', {},
     'comments-moderation-queue'),
    (r'^comments/', include('django.contrib.comments.urls')))

urlpatterns += patterns(
    '',
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout', {
            'next_page': '/'}),
    (r'^accounts/profile/', include('localtv.user_profile.urls')),
    (r'^accounts/', include('registration.backends.default.urls')),
    (r'^admin/edit_attributes/', include('localtv.inline_edit.urls')),
    (r'^admin/', include('localtv.admin.urls')),
    (r'^submit_video/', include('localtv.submit_video.urls')),
    (r'^listing/', include('localtv.listing.urls')),
    (r'^feeds/', include('localtv.feeds.urls')),
    (r'^goodies/', include('localtv.goodies.urls')),
    (r'^share/', include('email_share.urls')),
    (r'^widgets/', include('localtv.widgets.urls')))
