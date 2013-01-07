"""Base page for the Admin UI.

"""

from localtv.tests.selenium.pages.front.login import Login


class AdminNav(Login):
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
