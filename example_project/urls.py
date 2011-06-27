# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
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

def get_localtv_path(sub_path):
    import os
    import localtv
    base = os.path.abspath(os.path.join(os.path.dirname(localtv.__file__), '..'))
    return os.path.join(base, sub_path)

urlpatterns = patterns('',
                       (r'^(?P<path>(?:css|images|js|swf|versioned).*)', 'django.views.static.serve',
                        {'document_root': get_localtv_path('static')}),
                       (r'^localtv/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'localtv'}),
                       (r'^uploadtemplate/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'uploadtemplate'}),
                       #(r'^openid/', include('localtv_openid.urls')),
                       (r'', include('localtv.urls')),
                       )

