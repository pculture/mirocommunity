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
from ..page import Page

class MyOpenIDAuth(Page):
    _OPENID_PAGE = "html head base[href='https://www.myopenid.com/']"
    _CONTINUE = "button#continue-button"
    _PASSWORD = "form#password-signin-form td input#password"
    _SUBMIT = "input#signin_button"

    def myopenid_login(self, user, passw, **kwargs):
        """Login to openid.

        """
        if self.is_element_present(self._OPENID_PAGE):
            time.sleep(3)
            if self.is_element_present(self._PASSWORD):
                self.type_by_css(self._PASSWORD, passw)
                self.click_by_css(self._SUBMIT)
            if self.is_element_present(self._CONTINUE):
                self.click_by_css(self._CONTINUE)

