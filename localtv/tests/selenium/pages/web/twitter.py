from localtv.tests.selenium.pages import Page


class TwitterAuth(Page):
    """Twitter Auth page.

    """
    _TWITTER_PAGE = "Authorize Miro Community to use your account?"
    _USERNAME = "input#username_or_emai"
    _PASSWORD = "input#password"
    _SUBMIT = "input#allow"

    def twitter_login(self, user, passw, **kwargs):
        """Login to twitter.

        """
        if self.is_text_present("div.auth h2", self._TWITTER_PAGE):
            self.type_by_css(self._USERNAME, user)
            self.type_by_css(self._PASSWORD, passw)
            self.click_by_css(self._SUBMIT)
