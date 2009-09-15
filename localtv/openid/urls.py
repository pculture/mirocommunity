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

from localtv.openid.views import redirect_to_login_or_register

urlpatterns = patterns(
    '',
    (r'^$', 'django_openidconsumer.views.begin',
     {'sreg': 'email,nickname'}, 'localtv_openid_start'),
    (r'^complete/$', 'django_openidconsumer.views.complete',
     {'on_success': redirect_to_login_or_register}, 'localtv_openid_complete'),
    (r'^login_or_register/$', 'localtv.openid.views.login_or_register',
     {}, 'localtv_openid_login_or_register'),
    (r'^signout/$', 'localtv.openid.views.signout',
     {}, 'localtv_openid_signout'),
)

