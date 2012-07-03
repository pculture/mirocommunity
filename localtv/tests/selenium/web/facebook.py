from ..page import Page

class FacebookAuth(Page):
    _FB_LOGIN_PAGE = "html#facebook"
    _USERNAME = "input#email"
    _PASSWORD = "input#pass"
    _SUBMIT = "input[name='login']"

    def fb_login(self, user, passw, **kwargs):
        if self.is_element_present(self._FB_LOGIN_PAGE):
            self.click_by_css(self._USERNAME)
            self.click_by_css(self._PASSWORD)
            self.click_by_css(self._SUBMIT)

