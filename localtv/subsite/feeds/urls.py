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

from django.conf.urls.defaults import patterns, include

urlpatterns = patterns(
    'localtv.subsite.feeds.views',
    (r'^new/$', 'new', {}, 'localtv_subsite_feeds_new'),
    (r'^featured/$', 'featured', {}, 'localtv_subsite_feeds_featured'),
    (r'^popular/$', 'popular', {}, 'localtv_subsite_feeds_popular'))
