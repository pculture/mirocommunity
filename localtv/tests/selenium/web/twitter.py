from ..page import Page

class TwitterAuth(Page):
    _TWITTER_PAGE = "Authorize Miro Community to use your account?"
    _USERNAME = "input#username_or_emai"
    _PASSWORD = "input#password"
    _SUBMIT = "input#allow"

    def twitter_login(self, user, passw, **kwargs):
        if self.is_text_present("div.auth h2", self._TWITTER_PAGE):
            self.click_by_css(self._USERNAME)
            self.click_by_css(self._PASSWORD)
            self.click_by_css(self._SUBMIT)

