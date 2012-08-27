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
"""Test the Ability to create users via the Admin UI.

"""

from django.conf import settings
from localtv.tests.selenium.webdriver_base import WebdriverTestCase
from localtv.tests.selenium.front_pages import user_nav

class CreateUser(WebdriverTestCase):
    def setUp(self):
        WebdriverTestCase.setUp(self)
        self._pg = user_nav.NavPage(self)

    def test_create_user__admin_ui():
        """Create a user via the admin ui.

        """
        assert False, 'This test needs to be created'

    def test_create_user_mismatch_password(self):
        """Enter mismatched passwords on user creation.

        """
        assert False, 'This test needs to be created'

    def test_create_user__invalid_email(self):
        """Create a user with an invalid email.

        """
        assert False, 'This test needs to be created'

    def test_create__admin_user(self):
        """Create a user with admin privilages.

        """
        assert False, 'This test needs to be created'

    def test_change_user_privilages(self):
        """Elevate a regular user to an Admin.

        """
        assert False, 'This test needs to be created'

