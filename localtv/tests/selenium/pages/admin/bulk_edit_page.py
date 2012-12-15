#!/usr/bin/env python
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

"""The Bulk Edit Admin page.

"""
from localtv.tests.selenium.pages.admin.admin_nav import AdminNav




class BulkEditPage(AdminNav):
    """Describes elements and functions for the Admin Settings page.

    """

    _URL = 'admin/bulk_edit/'

    _FILTER = 'select.behave'  # Filters are name = category, author, filter

    _SEARCH = 'input[name="q"]'
    _SUBMIT_SEARCH = 'button.med_button[type="submit"]'

    _BULK_EDIT = 'select#bulk_action_selector'
    _BULK_EDIT_APPLY = 'div.bulkedit_controls button'

    #BULK EDIT FORM
    _TITLE_EDIT = 'li.title_edit input'
    _THUMB_EDIT = 'li.thumb_edit input'
    _DATE_EDIT = 'li.date_edit input'
    _DESCRIPTION_EDIT = 'li.description_edit input'
    _TAGS_EDIT = 'li.tags_edit'
    _CATEGORIES_EDIT = 'li.categories_edit'
    _USERS_EDIT = 'li.users_edit'
    _SUBMIT_BULK_FORM = 'div#massedit button'
    _CLOSE_BULK_FORM = 'div#massedit div.close'

    #VIDEOS TABLE
    _SELECT_ALL = 'th.checkbox input#toggle_all'
    _VIDEO_TITLE = 'tbody tr td:nth-child(2) span'

    def _bulk_edit_action(self, action):
        """Choose one of the bulk edit options.

        actions = Bulk Actions, Edit, Delete, Approve, Unapprove, 
        Feature, Unfeature
        """
        if self._items_in_table() is True:
            self.select_option_by_text(self._BULK_EDIT, action)
            self.click_by_css(self._BULK_EDIT_APPLY)
        else:
            print 'no items in the table'

    def _search(self, term):
        """Search in the bulk edit form.

        """
        self.type_by_css(self._SEARCH, term)
        self.click_by_css(self._SUBMIT_SEARCH)

    def _select_all_visible(self):
        """Select all visible items.

        """
        self.click_by_css(self._SELECT_ALL)

    def _items_in_table(self):
        """Return true if the table isn't empty.

        """
        return self.is_element_present(self._VIDEO_TITLE)

    def _filter_view(self, item_filter, option):
        """Filter the items based on provided options.

        """
        pass
        #Show All Categories - category default
        #Show All Users - user default
        #Current Videos - video default
        #Featured Videos
        #Rejected Videos
        #Featured Videos
        #Unapproved Videos
        #Videos without Attribution
        #Videos without Category

    def open_bulk_page(self):
        """Open the Bulk Edit page.
  
        """
        self.open_admin_page(self._URL)

    def search_and_bulk_delete(self, term):
        """Search for items and delete them all.

        """
        self._search(term)
        self._select_all_visible()
        self._bulk_edit_action("Delete")
