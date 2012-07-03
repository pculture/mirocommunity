#!/usr/bin/env python
from admin_nav import AdminNav


class ManagePage(AdminNav):
    """Describes elements and functions for the Manage Sources Admin page.

    """


    _URL = 'admin/manage/'
    _SEARCH_VIDEO = 'a[rel="#admin_search_sources"]'
    _ADD_FEED = 'a[rel="#admin_feed_add"]'


    _CLOSE_OVERLAY = 'div.close'
    # ADD FEED OVERLAY
    _FEED_URL = 'div#admin_feed_add input#id_feed_url'
    _SUBMIT_FEED = 'div#admin_feed_add button[type="submit"]'

    # REVIEW SUBMITTED FEED
    _FEED_NAME = 'div.floatleft h3'
    _FEED_SOURCE = '.video_service'
    _VID_COUNT = '.video_count'
    _ADD = 'button.add'
    _CANCEL = 'button.reject_button'
    _APPROVE_ALL = 'input#id_auto_approve_0'
    _REVIEW_FIRST = 'input#id_auto_approve_1'
    _REVIEW_SUBMIT = 'body.addingfeed button.add'


        
    #ADD SEARCH FEED OVERLAY
    _SEARCH_TEXT = 'input.livesearch_feed_url'
    _ORDER_SEARCH = 'select[name="order_by"]'  #options are "Latest" and "Relevance"
    _SUBMIT_SEARCH = 'div#admin_search_sources button[type="submit"]'


    #FEED TABLE
    _SELECT_ALL = 'input#toggle_all'
    _CAT_FILTER = 'select.behave[name="category"]' #default 'Show All Categories'
    _USER_FILTER = 'select.behave[name="author"]'  #default 'Show All Users'
    _TEXT_FILTER = 'input[placeholder="Search Sources"]' 
    _SUBMIT_FILTER = 'form.search_sources button[type="submit"]'
    _FEED_TITLE = 'tr td:nth-child(2) span'

    _VIDEO_SOURCE_FILTER = 'ul.only_show li a[href*="%s"]' #default '/admin/manage/', options user, search, feed
    _INVALID_FEED_TEXT = "* It does not appear that %s is an RSS/Atom feed URL."
    #BULK CONTROLS
    _BULK_EDIT = 'select#bulk_action_selector'
    _BULK_EDIT_APPLY = 'div.bulkedit_controls button'

       
    def open_manage_page(self, **kwargs):
        self.open_admin_page(self._URL)

    def submit_feed(self, **kwargs):
        default_data = {'feed url': None,
                     'feed name': None,
                     'feed author': None,
                     'feed source': None,
                     'approve all': True
                     }
        feed_data = default_data 
        feed_data.update(kwargs)
        self.click_by_css(self._ADD_FEED)
        self._add_feed_form(feed_data['feed url'])
        if feed_data['feed source'] == 'invalid':
            error_txt = self._INVALID_FEED_TEXT % feed_data['feed url']
            print error_txt
            if self.is_text_present('body', error_txt):
                return True
        else: 
            self._review_feed_form(feed_data['approve all'])
            return self._feed_in_table(feed_data['feed name'])
        

    def search_and_bulk_delete_feed(self, feed):
        self._search(feed)
        self._select_all_visible()
        self._bulk_edit_action("Remove")

    def delete_all_feeds(self):
        self._select_all_visible()
        self._bulk_edit_action("Delete")

    def filter_by_source(self,  source_type=None):
        """The default no-filture url is the page url (/admin/manage/), filter options are user, search or feed.

        """
        if source_type == None:
            source_type = self._URL
        self.click_by_css(self._VIDEO_SOURCE_FILTER % source_type)


    def _add_feed_form(self, url):
        self.type_by_css(self._FEED_URL, url)
        self.click_by_css(self._SUBMIT_FEED)

    def _review_feed_form(self, auto_approve):
        if not self._duplicate_feed():
        #FIX ME - Verify displayed data
            if auto_approve == True:
                self.check(self._APPROVE_ALL)
            else:
                self.check(self._REVIEW_FIRST)
            self.click_by_css(self._REVIEW_SUBMIT)
 

    def _duplicate_feed(self):
        if self.is_text_present('body', '* That feed already exists on this site.'):
            print 'feed is already added'
            self.open_manage_page()
            return True

    def _bulk_edit_action(self, action):
        """Choose one of the bulk edit options.

        actions = Bulk Actions, Edit, Remove
        """
        if self._items_in_table() == True:
            self.select_option_by_text(self._BULK_EDIT, action)
            self.click_by_css(self._BULK_EDIT_APPLY)
        else:
            print 'no items in the table'
      
    def _select_all_visible(self):
        print 'selecting all visible items'
        self.click_by_css(self._SELECT_ALL)
 
    def _feed_in_table(self, feed_title):
        return self.is_text_present(self._FEED_TITLE, feed_title)
         
