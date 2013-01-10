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

from localtv.tests.selenium import WebdriverTestCase
from localtv.tests.selenium.pages.front import listing_page
from django.core import management
import datetime


class ListingPages(WebdriverTestCase):
    """Tests for the various listing pages, new, featured and popular.

    """

    def setUp(self):
        WebdriverTestCase.setUp(self)
        self.listing_pg = listing_page.ListingPage(self)

    def test_new__thumbs(self):
        """Verify New listing page has expected thumbnails.

        """
        #CREATE 5 REGULAR VIDEOS
        for x in range(5):
            vid_name = 'listing_test_' + str(x)
            self.create_video(name=vid_name,
                              update_index=True)

        self.listing_pg.open_listing_page('new')
        self.assertEqual(True, self.listing_pg.has_thumbnails())
        self.assertEqual(True, self.listing_pg.thumbnail_count(5))
        self.assertEqual(True, self.listing_pg.valid_thumbnail_sizes(162, 117))

    def test_new__pagination(self):
        """New listing page is limited to 15 videos per page.

        """
        #CREATE 45 REGULAR VIDEOS
        for x in range(45):
            vid_name = 'listing_test_' + str(x)
            self.create_video(name=vid_name,
                              update_index=True)

        self.listing_pg.open_listing_page('new')
        self.assertEqual(True, self.listing_pg.has_thumbnails())
        self.assertEqual(True, self.listing_pg.thumbnail_count(15))

    def test_featured__pagination(self):
        """Featured listing page is limited to 15 videos per page.

        """

        #CREATE 60 FEATURED VIDEOS
        for x in range(60):
            vid_name = 'listing_test_' + str(x)
            self.create_video(name=vid_name,
                              watches=5,
                              last_featured=datetime.datetime.now(),
                              categories=None,
                              authors=None,
                              tags=None,
                              update_index=True)
        self.listing_pg.open_listing_page('featured')
        self.assertEqual(True, self.listing_pg.has_thumbnails())
        self.assertEqual(True, self.listing_pg.thumbnail_count(15))

    def test_featured__rss(self):
        """Featured listing page rss exists.

        """

        #CREATE 20 FEATURED VIDEOS
        for x in range(20):
            vid_name = 'listing_test_' + str(x)
            self.create_video(name=vid_name,
                              watches=5,
                              last_featured=datetime.datetime.now(),
                              categories=None,
                              authors=None,
                              tags=None,
                              update_index=True)
        self.listing_pg.open_listing_rss_page('featured')

    def test_popular__thumbs(self):
        """Verify Popular listing page has expected thumbnails.

        """

        #CREATE 5 REGULAR VIDEOS
        for x in range(5):
            vid_name = 'listing_test_' + str(x)
            self.create_video(name=vid_name,
                              watches=0,
                              update_index=True)
        #CREATE 30 POPULAR VIDEOS WITH NUM WATCHES THAT MATCH THE
        #NUM in the VID NAME
        for x in range(11, 41):
            vid_name = 'listing_test_' + str(x)
            self.create_video(name=vid_name,
                              watches=x * 2,
                              update_index=True)
        management.call_command('update_popularity')

        self.listing_pg.open_listing_page('popular')
        self.assertEqual(True, self.listing_pg.has_thumbnails())
        self.assertEqual(True, self.listing_pg.valid_thumbnail_sizes(162, 117))

    def test_featured__thumbs(self):
        """Verify Featured listing page has expected thumbnails.

        """

        self.listing_pg = listing_page.ListingPage(self)
        #CREATE 5 REGULAR VIDEOS
        for x in range(5):
            vid_name = 'listing_test_' + str(x)
            self.create_video(name=vid_name,
                              update_index=True)

        #CREATE VIDEOS THAT ARE FEATURED
        for x in range(16, 21):
            vid_name = 'listing_test_' + str(x)
            self.create_video(name=vid_name,
                              last_featured=datetime.datetime.now(),
                              update_index=True)
        self.listing_pg.open_listing_page('featured')
        self.assertEqual(True, self.listing_pg.has_thumbnails())
        self.assertEqual(True, self.listing_pg.valid_thumbnail_sizes(162, 117))
        #Only the 5 Featured Videos should be displayed on the Page
        self.assertEqual(True, self.listing_pg.thumbnail_count(5))

    def test_new__title(self):
        """Verify videos listed have titles that are links to vid page.

        """
        title = 'webdriver test video'
        user = self.create_user(username='autotester',
                                first_name='selene', last_name='driver')
        video = self.create_video(name=title,
                                  description=('This is the most awesome test '
                                               'video ever!'),
                                  user=user,
                                  categories=[self.create_category(name='webdriver',
                                                                   slug='webdriver')])
        self.listing_pg.open_listing_page('new')
        self.assertTrue(self.listing_pg.has_title(title))
        elem = self.browser.find_element_by_css_selector(self.listing_pg._TITLE)
        elem.click()
        self.assertTrue(self.browser.current_url.endswith(video.get_absolute_url()))

    def test_listing__overlay(self):
        """Verify overlay appears on hover and has description text.

        """
        title = 'webdriver test video'
        description = 'This is the most awesome test video ever'
        video = self.create_video(name=title,
                                  description=description)

        self.listing_pg.open_listing_page('new')

        has_overlay, overlay_description = self.listing_pg.has_overlay(video)
        self.assertTrue(has_overlay)
        self.assertIn(description, overlay_description)

    def test_listing__author(self):
        """Verify overlay appears on hover and has author text.

        """

        title = 'webdriver test video'
        description = 'This is the most awesome test video ever'
        self.create_user(username='autotester',
                         first_name='webby', last_name='driver')
        video = self.create_video(name=title,
                                  description=description,
                                  authors=[3],
                                  watches=1)
        self.listing_pg.open_listing_page('popular')
        _, overlay_text = self.listing_pg.has_overlay(video)

        self.assertIn('webby driver', overlay_text)
        self.assertIn('/author/3/', overlay_text)

    def test_new__page_name(self):
        """Verify new page display name on page.

        """
        self.listing_pg.open_listing_page('new')
        self.assertEqual('New Videos', self.listing_pg.page_name())

    def test__new__page_rss(self):
        """Verify new page rss feed url link is present.

        """
        self.listing_pg.open_listing_page('new')
        feed_url = self.base_url + self.listing_pg._FEED_PAGE % 'new'
        self.assertEqual(feed_url, self.listing_pg.page_rss())

    def test_popular__page_name(self):
        """Verify popular page display name on page.

        """
        self.listing_pg.open_listing_page('popular')
        self.assertEqual('Popular Videos', self.listing_pg.page_name())

    def test_listing_popular__page_rss(self):
        """Verify popular page rss feed url link is present.

        """

        self.listing_pg.open_listing_page('popular')
        feed_url = self.base_url + self.listing_pg._FEED_PAGE % 'popular'
        self.assertEqual(feed_url, self.listing_pg.page_rss())

    def test_featured__page_name(self):
        """Verify featured page display name on page.

        """
        self.listing_pg.open_listing_page('featured')
        self.assertEqual('Featured Videos', self.listing_pg.page_name())

    def test_listing_featured__page_rss(self):
        """Verify listing page rss feed url link is present.

        """
        self.listing_pg.open_listing_page('featured')
        feed_url = self.base_url + self.listing_pg._FEED_PAGE % 'featured'
        self.assertEqual(feed_url, self.listing_pg.page_rss())

    def published(self, listing):
        """Verify videos display published date (if configured)."""
        assert False, 'this needs to be implemented'
