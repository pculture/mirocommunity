"""The Admin Mange page which controls the feeds.

"""
from localtv.tests.selenium.pages.admin.admin_nav import AdminNav


class ManagePage(AdminNav):
    """Describes elements and functions for the Manage Sources Admin page.

    """

    _URL = 'admin/manage/'
    _SEARCH_VIDEO = 'a[rel="#admin_search_sources"] span'
    _ADD_FEED = 'a[href*="feed/add"] span'

    _CLOSE_OVERLAY = 'div.close'
    # ADD FEED OVERLAY
    _FEED_URL = 'input#id_feed_url'
    _SUBMIT_FEED = 'button[type="submit"]'

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

    # options are "Latest" and "Relevance"
    _ORDER_SEARCH = 'select[name="order_by"]'

    _SUBMIT_SEARCH = 'div#admin_search_sources button[type="submit"]'

    #FEED TABLE
    _SELECT_ALL = 'input#toggle_all'

    # default 'Show All Categories'
    _CAT_FILTER = 'select.behave[name="category"]'
    _USER_FILTER = 'select.behave[name="author"]'
    _TEXT_FILTER = 'input[placeholder="Search Sources"]'
    _SUBMIT_FILTER = 'form.search_sources button[type="submit"]'
    _FEED_TITLE = 'tr td:nth-child(2) span'
    _VIEW_FEED_LINK = "div.actions a.view_icon"
    _DELETE_FEED_LINK = ("td span.overflow:contains('%s') + "
                         "div.actions a.delete_icon")
    _EDIT_FEED_LINK = "td span.overflow:contains('%s') + div.actions a"

    # default '/admin/manage/', options user, search, feed
    _VIDEO_SOURCE_FILTER = 'ul.only_show li a[href*="%s"]'
    _INVALID_FEED_TEXT = "* It does not appear that %s is an RSS/Atom feed URL."

    #BULK CONTROLS
    _BULK_EDIT = 'select#bulk_action_selector'
    _BULK_EDIT_APPLY = 'div.bulkedit_controls button'

    def open_manage_page(self):
        """Open the manage page via the url.

        """
        self.open_admin_page(self._URL)

    def submit_feed(self, **kwargs):
        """Submit a feed.

        """
        default_data = {'feed url': None,
                        'feed name': None,
                        'feed author': None,
                        'feed source': None,
                        'approve all': True
                        }
        feed_data = default_data
        feed_data.update(kwargs)
        self.click_by_css(self._ADD_FEED)
        self._add_feed_form(**feed_data)
        if feed_data['feed source'] is 'duplicate':
            print '*** Expected this to be a duplicate feed. ***'
            return self._duplicate_feed()
        return self._feed_in_table(feed_data['feed name'])

    def delete_all_feeds(self):
        """Delete all the feeds on the page.

        """
        self._select_all_visible()
        self._bulk_edit_action("Delete")

    def filter_by_source(self, source_type=None):
        """Filter by the source type.

        The default no-filter url is the page url (/admin/manage/),
        filter options are user, search or feed.
        """
        if source_type is None:
            source_type = self._URL
        self.click_by_css(self._VIDEO_SOURCE_FILTER % source_type)

    def _add_feed_form(self, **kwargs):
        """Enter the feed url in the form field.

        """
        self.type_by_css(self._FEED_URL, kwargs['feed url'])
        if kwargs['approve all']:
            self.check(self._APPROVE_ALL)
        else:
            self.check(self._REVIEW_FIRST)
        elem = self.browser.find_element_by_css_selector(self._SUBMIT_FEED)
        elem.submit()

    def _duplicate_feed(self):
        """Return True if the feed is a duplicated.

        """
        dup_feed_message = 'Feed with this URL already exists.'

        if self.verify_text_present('li', dup_feed_message):
            print '*** got dup feed message *** '
            return True

    def _bulk_edit_action(self, action):
        """Choose one of the bulk edit options.

        actions = Bulk Actions, Edit, Remove
        """
        self.select_option_by_text(self._BULK_EDIT, action)
        self.click_by_css(self._BULK_EDIT_APPLY)

    def _select_all_visible(self):
        """Select all visible items in the table.

        """
        self.click_by_css(self._SELECT_ALL)

    def _feed_in_table(self, feed_title):
        """Boolean for whether the feed is listed in the table.

        """
        return self.is_text_present(self._FEED_TITLE, feed_title)

    def feed_table_element(self, feedname):
        """Return the webdriver element for the feed with the given title.

        """
        feed_els = self.browser.find_elements_by_css_selector(
            "td span.overflow")
        for feed_el in feed_els:
            if feed_el.text == feedname:
                return feed_el

    def click_feed_action(self, feedname, action):
        """Click the action link for the given feedname.

        Action must be one of display links for the feed: Edit, View, Delete
        """
        feed_el = self.feed_table_element(feedname)
        if not feed_el:
            self.record_error('feed not found in table')
        parent_el = feed_el.parent
        parent_el.find_element_by_link_text(action).click()
