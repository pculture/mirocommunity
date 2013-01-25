import os
import logging
from django.test import LiveServerTestCase
from localtv.tests import BaseTestCase
from selenium import webdriver
from django.conf import settings
from django.contrib.sites.models import Site
from django.core import management

class WebdriverTestCase(LiveServerTestCase, BaseTestCase):

    # Subclasses can set this to False to reuse the same browser from test-case
    # to test-case.
    NEW_BROWSER_PER_TEST_CASE = True

    # Selenium browser to use in the tests
    browser = None

    @classmethod
    def setUpClass(cls):
        super(WebdriverTestCase, cls).setUpClass()
        management.call_command('clear_index', interactive=False)
        cls.logger = logging.getLogger('test_steps')
        cls.logger.setLevel(logging.INFO)
        site_obj =  Site.objects.get_current()
        site_obj.domain = '%s:%s' % (cls.server_thread.host, 
                                     cls.server_thread.port)
        site_obj.save()
        if not cls.NEW_BROWSER_PER_TEST_CASE:
            cls.create_browser()
        

    @classmethod
    def tearDownClass(cls):
        if not cls.NEW_BROWSER_PER_TEST_CASE:
            cls.destroy_browser()
        #destroy the selenium browser before teardown to avoid liveserver
        #shutdown errors.  See https://code.djangoproject.com/ticket/19051
        super(WebdriverTestCase, cls).tearDownClass()
 

    def setUp(self):
        super(WebdriverTestCase, self).setUp()
        #Set up logging to capture the test steps.
        self.logger.info('testcase: %s' % self.id())
        self.logger.info('description: %s' % self.shortDescription())
        if self.NEW_BROWSER_PER_TEST_CASE:
            self.__class__.create_browser()
        
    def tearDown(self):
        if self.use_sauce:
            self.logger.info("Link to the job: https://saucelabs.com/jobs/%s"
                             % self.browser.session_id)
            self.logger.info("SauceOnDemandSessionID={0} job-name={1}".format(
                             self.browser.session_id, self.id()))
        if self.NEW_BROWSER_PER_TEST_CASE:
            self.__class__.destroy_browser()

    @classmethod
    def create_browser(cls):
        #If running on sauce config values are from env vars 
        cls.use_sauce = os.environ.get('USE_SAUCE', False)
        if cls.use_sauce: 
            cls.sauce_key = os.environ.get('SAUCE_API_KEY')
            cls.sauce_user = os.environ.get('SAUCE_USER_NAME')
            test_browser = os.environ.get('SELENIUM_BROWSER', 'Chrome').upper()
            dc = getattr(webdriver.DesiredCapabilities, test_browser)

            dc['version'] = os.environ.get('SELENIUM_VERSION', '')
            dc['platform'] = os.environ.get('SELENIUM_PLATFORM', 'WINDOWS 2008')
            dc['name'] = cls.__name__
            dc['tags'] = [os.environ.get('JOB_NAME', 'mc-local'),] 

            #Setup the remote browser capabilities
            cls.browser = webdriver.Remote(
                desired_capabilities=dc,
                command_executor=("http://{0}:{1}@ondemand.saucelabs.com:80/"
                                  "wd/hub".format(cls.sauce_user, cls.sauce_key)))

        #Otherwise just running locally - setup the browser to use.
        else:
            test_browser = os.environ.get('TEST_BROWSER', 'Firefox')
            cls.browser = getattr(webdriver, test_browser)()
        cls.base_url = ('http://%s:%s/' % (cls.server_thread.host, 
                                           cls.server_thread.port))

            
    @classmethod
    def destroy_browser(cls):
        if cls.browser is not None:
            cls.browser.quit()
            cls.browser = None
