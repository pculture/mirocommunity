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

