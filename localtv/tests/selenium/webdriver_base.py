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

from django.core import management
from django.test import LiveServerTestCase
from localtv.tests.base import BaseTestCase
from localtv.tests.selenium import pcfwebqa

class WebdriverTestCase(LiveServerTestCase, BaseTestCase):
    def setUp(self):
        super(WebdriverTestCase, self).setUp()
        management.call_command('clear_index', interactive=False)
        LiveServerTestCase.setUp(self)
        setattr(pcfwebqa, 'base_url', self.live_server_url+'/')
        pcfwebqa.browser.get(pcfwebqa.base_url)
        BaseTestCase.setUp(self)
        self.admin_user = pcfwebqa.admin_user
        self.admin_pass = pcfwebqa.admin_pass
        self.normal_user = pcfwebqa.normal_user
        self.normal_pass = pcfwebqa.normal_pass
        self.create_user(username=self.admin_user, password=self.admin_pass, is_superuser=True)
        self.create_user(username=self.normal_user, password=self.normal_pass)
      

