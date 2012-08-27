#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

"""The /listing pages.

"""
from ..page import Page
import time


class ListingPage(Page):
    """Define all the elements common to the listing pages.

    """
    _NEW_PAGE = 'listing/new/'
    _POPULAR_PAGE = 'listing/popular/'
    _FEATURED_PAGE = 'listing/featured/'
    _CATEGORY_PAGE = 'category/%s'
    _THUMBNAIL = '.video-thumb-wrapper img'
    _TITLE = 'a.title-link'
    _FEED_PAGE = 'feeds/%s'
    _HOVER = '.popover-trigger'
    _BYLINE = '.byline a'
    _PAGE_NAME = 'header.page-header h1'
    _PAGE_RSS = 'header.page-header a.rss'

    def page_name(self):
        """Return the name of the page from the heading.

        """
        return self.get_text_by_css(self._PAGE_NAME)

    def page_rss(self):
        """Return the page rss feed link.

        """
        return self.get_element_attribute(self._PAGE_RSS, 'href')

    def open_listing_page(self, listing):
        """Open the given listing page.

       """
        valid_pages = ('new', 'popular', 'featured')
        if listing not in valid_pages:
            assert False, "page must be either %s pages" % str(valid_pages)
        listing_pg_url = getattr(self, "_".join(['', listing.upper(), 'PAGE']))
        self.open_page(listing_pg_url)

    def open_listing_rss_page(self, listing):
        """Open the /feed/ page of the giving listing page.

        """
        valid_pages = ('new', 'popular', 'featured')
        if listing not in valid_pages:
            assert False, "page must be either %s pages" % str(valid_pages)
        self.open_page(self._FEED_PAGE % listing)

    def open_category_page(self, category):
        """Open a category page via the url.

        """
        category_pg_url = self._CATEGORY_PAGE % category
        self.open_page(category_pg_url)

    def has_thumbnails(self):
        """Return True if the displayed page has thumbnails.

        """
        time.sleep(2)
        if self.is_element_present(self._THUMBNAIL):
            return True

    def default_thumbnail_percent(self):
        """Return the percentage of default thumbnails on the page.

        """
        default_img_count = 0
        thmb_els = self.browser.find_elements_by_css_selector(self._THUMBNAIL)
        total_thumbnails = len(thmb_els)
        for thumb_el in thmb_els:
            png_file = thumb_el.get_attribute("src")
            if "nounproject_2650_television_white.png" in png_file:
                default_img_count += default_img_count
        percent_default = (default_img_count / float(total_thumbnails)) * 100
        return percent_default

    def thumbnail_count(self, expected):
        """Count the number of thumbnails dipslayed on the page.

        """
        visible_thumbs = self.count_elements_present(self._THUMBNAIL)
        if visible_thumbs is expected:
            return True
        else:
            return False, ("Found {0} thumbnail(s) on the page, expected "
                           "{1}".format(visible_thumbs, expected))

    def valid_thumbnail_sizes(self, height, width):
        """Verify thumbnails have the expected height / width attributes.

        """
        thumb_img = self._THUMBNAIL
        thumbs = self.browser.find_elements_by_css_selector(thumb_img)
        invalid_thumbs = []
        for elem in thumbs:
            size = elem.size
            if size['height'] != height and size['width'] != width:
                invalid_thumbs.append((size['height'], size['width']))
        if invalid_thumbs == []:
            return True
        else:
            return invalid_thumbs

    def has_title(self, expected):
        """Return when the the expected title is displayed.

        """
        return self.verify_text_present(self._TITLE, expected)

    def has_overlay(self, title_text):
        """"Return is the overlay displays and the text content.

        """
        elem = self.browser.find_element_by_link_text(title_text)
        self.hover_by_css(elem)
        if self.is_element_present(self._HOVER):
            overlay_text = self.get_element_attribute(
                self._HOVER, 'data-content')
            return True, overlay_text

    def title_link(self, title):
        """Return the url the Title link opens.

        """
        elem = self.browser.find_element_by_link_text(title)
        return elem.get_attribute('href')

    def author_link(self, title_text, author):
        """Return the auther text and the url the link opens.

        """
        elem = self.browser.find_element_by_link_text(title_text)
        self.hover_by_css(elem)
        overlay_byline = self.get_text_by_css(self._BYLINE)
        elem = self.browser.find_element_by_link_text(author)
        return overlay_byline, elem.get_attribute('href')
