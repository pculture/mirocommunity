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

from django.conf import settings
from django.conf.urls.defaults import url, patterns, include

from localtv.admin.base import registry, user_registry
from localtv.admin.views import ViewNameRedirectView

ADMIN_ROOT_VIEW = getattr(settings, 'LOCALTV_ADMIN_ROOT_VIEW',
                          'localtv_admin_dashboard')


urlpatterns = patterns('',
    url(r'^$', ViewNameRedirectView.as_view(url_name=ADMIN_ROOT_VIEW),
        name='localtv_admin_root'),
    url(r'^', include(user_registry.get_urlpatterns())),
    url(r'^', include(registry.get_urlpatterns())),

    # Shadow some paths to provide backwards-compatibility for templates from
    # a time when the views had different names. Since the paths are identical,
    # these views should never be reached - but if the path of the referenced
    # view changes, these views will still redirect properly.
    url(r'^$', ViewNameRedirectView.as_view(url_name=ADMIN_ROOT_VIEW),
        name='localtv_admin_index'),
    url(r'^profile/$',
        ViewNameRedirectView.as_view(url_name='localtv_admin_profile'),
        name='localtv_user_profile'),
    url(r'^playlists/$',
        ViewNameRedirectView.as_view(url_name='localtv_admin_playlist_list'),
        name='localtv_playlist_index'),

    # Redirect some old view names to the admin base.
    url(r'^$', ViewNameRedirectView.as_view(url_name=ADMIN_ROOT_VIEW),
        name='localtv_admin_reject_video'),
    url(r'^$', ViewNameRedirectView.as_view(url_name=ADMIN_ROOT_VIEW),
        name='localtv_admin_approve_video'),
    url(r'^$', ViewNameRedirectView.as_view(url_name=ADMIN_ROOT_VIEW),
        name='localtv_admin_unfeature_video'),
    url(r'^$', ViewNameRedirectView.as_view(url_name=ADMIN_ROOT_VIEW),
        name='localtv_admin_feature_video'),
    url(r'^(.+)$',
        ViewNameRedirectView.as_view(url_name='localtv_admin_playlist_list'),
        name='localtv_playlist_add_video'),
)
