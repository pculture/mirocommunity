import time
from django.conf import settings
from django.core import mail
from localtv.tests.selenium import WebdriverTestCase
from localtv.tests.selenium.pages.front.login import LoginPage 

class UserAuth(WebdriverTestCase):
    """Login tests for site, fb, twitter, google, open id...

    """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(UserAuth, cls).setUpClass()
        cls.create_user(username='user',
                        password='password')
        cls.login_pg = LoginPage(cls)

    def setUp(self):
        super(UserAuth, self).setUp()
        self.login_pg.open_page('login/')


    def tearDown(self):
        super(UserAuth, self).tearDown()
        self.browser.delete_all_cookies()
                
    def test_login__valid_site(self):
        """Login with valid site creds.

        """
        kwargs = {'user': 'user',
                  'passw': 'password',
                  'success': True}
        self.assertTrue(self.login_pg.login(**kwargs))

    def test_login__facebook(self):
        """Login with facebook creds.

        """
        if (getattr(settings, 'FACEBOOK_APP_ID', None) is None or
            getattr(settings, 'FACEBOOK_API_SECRET', None) is None):
            self.skipTest("Skipping, facebook auth not configured")

        kwargs = {'user': 'seleniumTestUser',
                  'passw': 'selenium',
                  'kind': 'facebook'}
        self.assertTrue(self.login_pg.login(**kwargs))

    def test_login__openid(self):
        """Login with openid (myopenid.com) creds.

        """
        kwargs = {'user': 'http://pcf-web-qa.myopenid.com/',
                  'passw': 'pcf.web.qa',
                  'kind': 'openid'}
        self.assertTrue(self.login_pg.login(**kwargs),
                        "Login failed at {0}".format(self.login_pg.current_url()))

    def test_login__google(self):
        """Login with google creds.

        """
        kwargs = {'user': 'pculture.qa@gmail.com',
                  'passw': 'Amara@Subtitles',
                  'kind': 'google'}

        self.assertTrue(self.login_pg.login(**kwargs))

    def test_login__twitter(self):
        """Login with twitter creds.

        """
        if (getattr(settings, 'TWITTER_CONSUMER_SECRET', None) is None or
            getattr(settings, 'TWITTER_CONSUMER_KEY', None) is None):
            self.skipTest("Skipping, twitter auth not configured")

        kwargs = {'user': 'PCFQA',
                  'passw': 'MiroCommunity',
                  'kind': 'twitter'}
        self.assertTrue(self.login_pg.login(**kwargs),
                        "Login failed at {0}".format(self.login_pg.current_url()))

    def test_login__bad_password(self):
        """Login with invalid password

        """
        kwargs = {'user': 'user',
                  'passw': 'junk',
                  'success': 'bad password'}
        self.assertFalse(self.login_pg.login(**kwargs))

    def test_login__signup_and_activate(self):
        """Sign up a new user, activate account and login.

        """

        kwargs = {'user': 'testuser' + str(time.time()),
                  'passw': 'test.pass',
                  'email': 'pculture.qa@gmail.com',
                  'kind': 'signup'}
        self.login_pg.login(**kwargs)
        #The second email sent has the activation link
        msg = str(mail.outbox[1].message())
        lines = msg.split('\n')
        for line in lines:
            if "accounts/activate" in line:
                activation_url = line.replace(
                    'http://example.com/', self.base_url)
                print activation_url
                break
        else:
            self.fail("Did not locate the activation url in the email message")

        kwargs['kind'] = 'site'
        self.login_pg.open_page(activation_url)
        kwargs['success'] = True
        self.assertTrue(self.login_pg.login(
            **kwargs), 'Login failed with new user account')

    def test_login__blank_value(self):
        """Login with  blank password.

        """
        kwargs = {'user': 'user',
                  'passw': '',
                  'success': 'blank value'}
        self.assertFalse(self.login_pg.login(**kwargs))

    def test_login__forgot(self):
        self.login_pg.wait_for_element_present(self.login_pg.LOGIN['css'])
        self.login_pg.click_by_css(self.login_pg.LOGIN['css'])
        self.assertTrue(self.login_pg.is_element_visible(self.login_pg._FORGOT_PASSWORD))
