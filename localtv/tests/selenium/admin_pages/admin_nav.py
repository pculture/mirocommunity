#!/usr/bin/env python
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
"""Base page for the Admin UI.

"""

from ..page import Page
from ..front_pages.login import Login


class AdminNav(Login, Page):
    """Define the common elments in the Admin UI.

    """

    _URL = '/admin/'

    def login(self, user, passw):
        """Login to the site.

        """
        self.open_page('accounts/login/')
        kwargs = {'user': user,
                  'passw': passw}
        self.user_login(**kwargs)

    def open_admin_page(self, url):
        """Open the admin page.

        """
        if not url:
            url = self._URL
        self.open_page(url)
