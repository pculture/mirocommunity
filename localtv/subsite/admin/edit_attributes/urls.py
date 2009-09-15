# Miro Community
# Copyright 2009 - Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    'localtv.subsite.admin.edit_attributes.feed_views',
    (r'^feed/(?P<id>[0-9]+)/name/$', 'edit_name',
     {}, 'localtv_admin_feed_edit_title'),
    (r'^feed/(?P<id>[0-9]+)/auto_categories/$', 'edit_auto_categories',
     {}, 'localtv_admin_feed_edit_auto_categories'),
    (r'^feed/(?P<id>[0-9]+)/auto_authors/$', 'edit_auto_authors',
     {}, 'localtv_admin_feed_edit_auto_authors'))
