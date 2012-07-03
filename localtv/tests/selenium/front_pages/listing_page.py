#!/usr/bin/env python
from ..page import Page

class ListingPage(Page):
    _NEW_PAGE = 'listing/new/' 
    _POPULAR_PAGE = 'listing/popular/'
    _FEATURED_PAGE = 'listing/featured/'
    _CATEGORY_PAGE = 'category/%s'
    _THUMBNAIL = 'li.media-item figure.thumb'
    _TITLE = 'h1.video-title a.title-link'
    _FEED_PAGE = 'feeds/%s'
    _HOVER = '.popover-normal-text'
    _BYLINE = '.byline'
    _PAGE_NAME = 'header.page-header h1'
    _PAGE_RSS =  'header.page-header a.rss'


    def page_name(self):
        return self.get_text_by_css(self._PAGE_NAME)

    def page_rss(self):
        return self.get_element_attribute(self._PAGE_RSS, 'href')

    def open_listing_page(self, listing):
        valid_pages = ('new', 'popular', 'featured')
        if listing not in valid_pages:
            assert False, "page must be either %s pages" % str(valid_pages)
        pg = getattr(self, "_".join(['', listing.upper(), 'PAGE']))
        self.open_page(pg)

    def open_listing_rss_page(self, listing):
        valid_pages = ('new', 'popular', 'featured')
        if listing not in valid_pages:
            assert False, "page must be either %s pages" % str(valid_pages)
        pg = getattr(self, "_".join(['', listing.upper(), 'PAGE']))
        self.open_page(self._FEED_PAGE % listing)


    def open_category_page(self, category):
        pg = self._CATEGORY_PAGE % category
        self.open_page(pg)


    def has_thumbnails(self):
        thumb_img = self._THUMBNAIL + " a"
        if self.is_element_present(thumb_img):
            return True


    def thumbnail_count(self, expected):
        visible_thumbs = self.count_elements_present(self._THUMBNAIL)
        if visible_thumbs == expected:
            return True
        else:
            return False, "Found {0} thumbnail(s) on the page, expected {1}".format(visible_thumbs, expected)


    def valid_thumbnail_sizes(self, height, width):
        thumb_img = self._THUMBNAIL + " a "
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
        return self.verify_text_present(self._TITLE, expected)

    def has_overlay(self, title_text):
        elem = self.browser.find_element_by_link_text(title_text)
        self.hover_by_css(elem)
        if self.is_element_present(self._HOVER):
            overlay_text = self.get_text_by_css(self._HOVER)
            return True, overlay_text
        

    def title_link(self, title):
        elem = self.browser.find_element_by_link_text(title)
        return elem.get_attribute('href')

   
    def author_link(self, title_text, author):
        elem = self.browser.find_element_by_link_text(title_text)
        self.hover_by_css(elem)
        overlay_byline = self.get_text_by_css(self._BYLINE)
        elem = self.browser.find_element_by_link_text(author)
        return overlay_byline, elem.get_attribute('href')    

        
