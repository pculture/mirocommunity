import time
from localtv.tests.selenium.pages import Page


class MyOpenIDAuth(Page):
    _OPENID_PAGE = "a[href='https://www.myopenid.com/']"
    _CONTINUE = "button#continue-button"
    _PASSWORD = "form#password-signin-form td input#password"
    _SUBMIT = "input#signin_button"

    def myopenid_login(self, user, passw, **kwargs):
        """Login to openid.

        """
        self.wait_for_element_present(self._OPENID_PAGE, wait_time=10)
        if self.is_element_present(self._PASSWORD):
            self.type_by_css(self._PASSWORD, passw)
            self.click_by_css(self._SUBMIT)
        if self.is_element_present(self._CONTINUE):
            self.click_by_css(self._CONTINUE)
