#!/usr/bin/env python
"""
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
"""

from localtv.tests.selenium.page import Page
from localtv.tests.selenium.front_pages.login import Login


class NavPage(Login, Page):
    """Parent of all pages, contains the Header and Footer navigation items.

    """

    #FOOTER NAVIGATION

    SITE_NAME = "a.site-name"

    LOGIN = {'css': ".nav-login a",
             'text': "Login"}

    FOOTER_HOME = {'css': "ul#footer_links li a[href='/'",
                   'text': "Home"}

    GOODIES = {'css': "a[href='/goodies/widget/']",
                      'text': "Goodies"
               }

    LOCAL_FOOTER = {'css': ".local_footer",
                    'text': 'custom'
                    }

    PROFILE = {'css': "a[href='/accounts/profile/']",
               'text': "Your Profile"}

    LOGOUT = {'css': "a[href*='/accounts/logout/?next=']",
              'text': "Logout %s"}

    #TOP PAGE NAVIGATION
    TOP_NAV = {'HOME': {"css": ".home_page",
                        "url": "/",
                        "text": "Home"},

               'FEATURED': {"css": ".featured",
                            "url": "/listing/featured",
                            "text": "Featured"},

               'NEW': {"css": ".new",
                              "url": "/listing/new",
                              "text": "New Videos"},

               'CATEGORIES': {"css": ".categories",
                              "url": "/listing/categories",
                              "text": "Categories"},

               'POPULAR': {"css": ".popular",
                           "url": "/listing/popular",
                           "text": "Popular"},

               'SUBMIT': {"css": ".submit",
                              "url": "/submit_video/",
                              "text": "Submit A Video"},

               'ABOUT': {"css": ".about",
                         "url": "/about/",
                         "text": "About Us"}
               }

    SEARCH_BOX = "form#search input#search_field"
    SEARCH_SUBMIT = "form#search button span.search-icon"

    ADMIN = {"css": "a[href='/admin/']",
             "text": "View Admin"}

    CATEGORY = ".categories ul li a[href='/category/%s/']"

    def site_name(self):
        """Returns the displayed site name.

        """
        return self.get_text_by_css(self.SITE_NAME)

    def is_logged_in(self):
        """Returns whether a user is logged in.

        """
        if self.is_element_present(self.LOGIN['css']):
            return False
        elif self.is_element_present(self.PROFILE['css']):
            return True

    def logout(self):
        """Logout current user.
 
        """
        if self.is_logged_in() is True:
            self.click_by_css(self.LOGOUT['css'])

    def login(self, user, passw, kind='site', email=None, success=True):
        """Log in with the specified account type - default as a no-priv user.

        Valid values for kind are: 'site', 'signup', 'facebook',
        'google', 'openid', 'twitter'

        """
        if self.is_logged_in() and not \
            self.is_text_present(self.LOGOUT['css'], 
                                 self.LOGOUT['text'] % user):
            self.logout()

        self.wait_for_element_present(self.LOGIN['css'])
        self.click_by_css(self.LOGIN['css'])
        kwargs = {'user': user,
                  'passw': passw,
                  'email': email,
                  'tab': kind,
                  'success': success,
                  }
        self.user_login(**kwargs)
        return self.is_logged_in()
