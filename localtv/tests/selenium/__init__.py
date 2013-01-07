import time
import os
import sys
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
        LiveServerTestCase.setUp(self)
        BaseTestCase.setUp(self)

        self.use_sauce = os.environ.get('USE_SAUCE', False)
        self.base_url = os.environ.get('TEST_URL', self.live_server_url + '/')
        self._clear_index()
        #If we are using sauce - check if we are running on jenkins.
        if self.use_sauce:
            self.sauce_key = os.environ.get('SAUCE_API_KEY')
            self.sauce_user = os.environ.get('SAUCE_USER_NAME')
            test_browser = os.environ.get('SELENIUM_BROWSER', 'CHROME')
            dc = getattr(webdriver.DesiredCapabilities,
                         test_browser.upper().replace(" ", ""))
            dc['version'] = os.environ.get('SELENIUM_VERSION', '')
            dc['platform'] = os.environ.get('SELENIUM_PLATFORM', 'WINDOWS 2008')
            dc['name'] = self.id()

            #Setup the remote browser capabilities
            self.browser = webdriver.Remote(
                desired_capabilities=dc,
                command_executor=("http://{0}:{1}@ondemand.saucelabs.com:80/"
                                  "wd/hub".format(self.sauce_user, self.sauce_key)))
            sys.stdout.write("SauceOnDemandSessionID={0} job-name={1}".format(
                self.browser.session_id, self.id()))
        #Otherwise just running locally - setup the browser to use.
        else:
            test_browser = getattr(settings, 'TEST_BROWSER')
            self.browser = getattr(webdriver, test_browser)()

        self.admin_user = 'seleniumTestAdmin'
        self.admin_pass = 'password'
        self.normal_user = 'seleniumTestUser'
        self.normal_pass = 'password'
        self.create_user(username=self.admin_user,
                         password=self.admin_pass, is_superuser=True)
        self.create_user(username=self.normal_user, password=self.normal_pass)
        self.browser.get(self.base_url)

    def tearDown(self):
        print("Link to the job: https://saucelabs.com/jobs/%s" % self.browser.session_id)
        # Sauce gets its own screenshots.
        if not self.use_sauce:
            try:
                time.sleep(2)
                screenshot_name = "%s.png" % self.id()
                filename = os.path.join(self.results_dir, screenshot_name)
                self.browser.get_screenshot_as_file(filename)
            except:
                # Sometimes screenshot fails - test should not fail on this.
                pass
        try:
            self.browser.quit()
        except:
            # May already be quit - so don't fail.
            pass
