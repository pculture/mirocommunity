"""Base page for the Admin UI.

"""
from localtv.tests.selenium.pages import Page
class AdminNav(Page):
    """Define the common elments in the Admin UI.

    """

    _URL = 'admin/'

    def open_admin_page(self, url):
        """Open the admin page.

        """
        if not url:
            url = self._URL
        self.open_page(url)
