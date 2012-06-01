# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = (
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) +
    static(settings.UPLOADTEMPLATE_MEDIA_URL,
           document_root=settings.UPLOADTEMPLATE_MEDIA_ROOT) +
    patterns('',
        url(r'^thumbs/', include('daguerre.urls')),
        url(r'^', include('localtv.contrib.contests.urls')),
        url(r'^', include('localtv.urls')),
    )
)
