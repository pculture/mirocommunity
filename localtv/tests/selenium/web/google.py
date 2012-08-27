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

"""Google specific login.

"""

from ..page import Page

class Google(Page):
    """Google login pages.

    """

    _GOOGLE_PAGE = "div.google-header-bar"
    _APPROVE = "input#approve_button"
    _EMAIL = "input#Email"
    _PASSWORD = "input#Passwd"
    _SUBMIT = "input#signIn.g-button"
   
    def google_login(self, user, passw, **kwargs):
        """Enter info into google login form.

        """
        if self.is_element_present(self._GOOGLE_PAGE):
            if self.is_element_present(self._EMAIL):
                self.type_by_css(self._EMAIL, user)
                self.type_by_css(self._PASSWORD, passw)
                self.click_by_css(self._SUBMIT)
            if self.is_element_present(self._APPROVE): 
                self.click_by_css(self._APPROVE)
 




