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
    "",
    (r'^$',
     'django.views.generic.simple.direct_to_template',
     {'template': 'localtv/mainsite/index.html'},
     'localtv_mainsite_index'),
    (r'^college/?$',
     'django.views.generic.simple.direct_to_template',
     {'template': 'localtv/mainsite/college.html'},
     'localtv_mainsite_index'),
    ('^signup/?$', 'localtv.mainsite.views.signup_for_site', {},
     'localtv_mainsite_signup'),
    )
