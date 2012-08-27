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

from django.conf import settings
from django.core import mail
from localtv.tests.selenium.webdriver_base import WebdriverTestCase
from localtv.tests.selenium.front_pages import user_nav


class UserAuth(WebdriverTestCase):
    """Login tests for site, fb, twitter, google, open id...

    """

    def setUp(self):
        WebdriverTestCase.setUp(self)
        self.nav_pg = user_nav.NavPage(self)

    def _auth_settings_not_configured(self, setting):
        """Verify secret keys are configured for fb and twitter auth.

        """
        if getattr(settings, setting) is None:
            return True

    def login_failed_at(self):
        """Return url where login failed.

        """
        msg = "Login failed at %s" % self.nav_pg.current_url()
        return msg

    def test_login__valid_site(self):
        """Login with valid site creds.

        """
        kwargs = {'user': 'seleniumTestUser',
                  'passw': 'password',
                  'success': True}
        self.assertTrue(self.nav_pg.login(**kwargs))

    def test_login__facebook(self):
        """Login with facebook creds.

        """
        if self._auth_settings_not_configured('FACEBOOK_SECRET_KEY'):
            self.skipTest("Skipping, facebook auth not configured")

        kwargs = {'user': 'seleniumTestUser',
                  'passw': 'selenium',
                  'kind': 'facebook'}
        self.assertTrue(self.nav_pg.login(**kwargs))

    def test_login__openid(self):
        """Login with openid (myopenid.com) creds.

        """
        kwargs = {'user': 'http://pcf-web-qa.myopenid.com/',
                  'passw': 'pcf.web.qa',
                  'kind': 'openid'}
        self.assertTrue(self.nav_pg.login(**kwargs), self.login_failed_at())

    def test_login__google(self):
        """Login with google creds.

        """
        kwargs = {'user': 'pculture.qa@gmail.com',
                  'passw': 'Amara@Subtitles',
                  'kind': 'google'}
        self.assertTrue(self.nav_pg.login(**kwargs))

    def test_login__twitter(self):
        """Login with twitter creds.

        """
        if self._auth_settings_not_configured('TWITTER_CONSUMER_SECRET'):
            self.skipTest("Skipping, twitter auth not configured")

        kwargs = {'user': 'PCFQA',
                  'passw': 'MiroCommunity',
                  'kind': 'twitter'}
        self.assertTrue(self.nav_pg.login(**kwargs), self.login_failed_at())

    def test_login__bad_password(self):
        """Login with invalid password

        """
        kwargs = {'user': 'seleniumTestUser',
                  'passw': 'junk',
                  'success': 'bad password'}
        self.assertFalse(self.nav_pg.login(**kwargs))

    def test_login__signup_and_activate(self):
        """Sign up a new user, activate account and login.

        """

        kwargs = {'user': 'testuser' + str(time.time()),
                  'passw': 'test.pass',
                  'email': 'pculture.qa@gmail.com',
                  'kind': 'signup',
                  }
        self.nav_pg.login(**kwargs)
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
        self.nav_pg.open_page(activation_url)
        kwargs['success'] = True
        self.assertTrue(self.nav_pg.login(
            **kwargs), 'Login failed with new user account')

    def test_login__blank_value(self):
        """Login with  blank password.

        """
        kwargs = {'user': 'seleniumTestUser',
                  'passw': '',
                  'success': 'blank value'}
        self.assertFalse(self.nav_pg.login(**kwargs))
