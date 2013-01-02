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

import time
import os
from django.core import management
from django.test import LiveServerTestCase
from localtv.tests import BaseTestCase
from selenium import webdriver
from django.conf import settings


class WebdriverTestCase(LiveServerTestCase, BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(WebdriverTestCase, cls).setUpClass()
        cls.results_dir = getattr(settings, "TEST_RESULTS_DIR")
        if not os.path.exists(cls.results_dir):
            os.makedirs(cls.results_dir)

    def setUp(self):
        super(WebdriverTestCase, self).setUp()
        """This is where we want to setup the browser configuation.

        If you want to use something other than default (no sauce on ff)
        then it should be setup as env vars in the system under test. When
        running sauce on jenkins with the jenkins pluging - then the vars are
        set there.
        Environment vars recognized by jenkins sauce plugin.
        SELENIUM_HOST - The hostname of the Selenium server
        SELENIUM_PORT - The port of the Selenium server
        SELENIUM_PLATFORM - The operating system of the selected browser
        SELENIUM_VERSION - The version number of the selected browser
        SELENIUM_BROWSER - The browser string.
        SELENIUM_URL - The initial URL to load when the test begins
        SAUCE_USER_NAME - The user name used to invoke Sauce OnDemand
        SAUCE_API_KEY - The access key for the user used to invoke Sauce OnDemand
        
        We are going to look for a USE_SAUCE = True if we are using sauce,
        and a default browser TEST_BROWSER if not using sauce.
        """

        self.use_sauce = os.environ.get('USE_SAUCE', False)
        self.base_url = os.environ.get('TEST_URL', 'http://127.0.0.1:8081/')
        self._clear_index()
        #If we are using sauce - check if we are running on jenkins.
        if self.use_sauce:
            sauce_key = os.environ.get('SAUCE_API_KEY')
            test_browser = os.environ.get('SELENIUM_BROWSER', 'CHROME')
            dc = getattr(webdriver.DesiredCapabilities, test_browser.upper())
            dc['version'] = os.environ.get('SELENIUM_VERSION', '')
            dc['platform'] = os.environ.get('SELENIUM_PLATFORM', 'WINDOWS 2008')
            dc['name'] = self.shortDescription()

            #Setup the remote browser capabilities
            self.browser = webdriver.Remote(
                desired_capabilities = dc,
                command_executor=("http://jed-pcf:%s@ondemand.saucelabs.com:80"
                                  "/wd/hub" % sauce_key)
                                  )

        #Otherwise just running locally - setup the browser to use.
        else:
            test_browser = os.environ.get('TEST_BROWSER', getattr(settings, 'TEST_BROWSER'))
            self.browser = getattr(webdriver, test_browser)()
            self.browser.implicitly_wait(1)

        LiveServerTestCase.setUp(self)
        BaseTestCase.setUp(self)
        self.admin_user = 'seleniumTestAdmin' 
        self.admin_pass = 'password'
        self.normal_user = 'seleniumTestUser'
        self.normal_pass = 'password'
        self.create_user(username=self.admin_user,
                         password=self.admin_pass, is_superuser=True)
        self.create_user(username=self.normal_user, password=self.normal_pass)
        self.browser.get(self.base_url)

    def tearDown(self):
        time.sleep(1)
        try:
            screenshot_name = "%s.png" % self.id()
            filename = os.path.join(self.results_dir, screenshot_name)
            self.browser.get_screenshot_as_file(filename)
        finally:
            self.browser.quit()
