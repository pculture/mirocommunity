
from django.conf import settings
from django.core import mail
from django.core import management

from localtv.tests.selenium.webdriver_base import WebdriverTestCase
from localtv.tests.selenium import pcfwebqa
from localtv.tests.selenium.front_pages import listing_page
from django.core import management
import datetime

class SeleniumTestCaseListingPages(WebdriverTestCase):
   
    def setUp(self):
        WebdriverTestCase.setUp(self)
        self.listing_pg = listing_page.ListingPage(pcfwebqa)

    def test_new_listing__thumbs(self):
        #CREATE 5 REGULAR VIDEOS
        for x in range(5):
            vid_name = 'listing_test_'+str(x)
            self.create_video(name=vid_name,
                              update_index=True)

        self.listing_pg.open_listing_page('new')
        self.assertEqual(True, self.listing_pg.has_thumbnails())
        self.assertEqual(True, self.listing_pg.thumbnail_count(5))
        self.assertEqual(True, self.listing_pg.valid_thumbnail_sizes(140, 194))
    

    def test_new_listing__pagination(self):
        #CREATE 45 REGULAR VIDEOS
        for x in range(45):
            vid_name = 'listing_test_'+str(x)
            self.create_video(name=vid_name,
                              update_index=True)

        self.listing_pg.open_listing_page('new')
        self.assertEqual(True, self.listing_pg.has_thumbnails())
        self.assertEqual(True, self.listing_pg.thumbnail_count(15))


    def test_featured_listing__pagination(self):
        #CREATE 60 FEATURED VIDEOS
        for x in range(60):
            vid_name = 'listing_test_'+str(x)
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

    def test_featured_listing__rss(self):
        #CREATE 20 FEATURED VIDEOS
        for x in range(20):
            vid_name = 'listing_test_'+str(x)
            self.create_video(name=vid_name,
                              watches=5, 
                              last_featured=datetime.datetime.now(), 
                              categories=None, 
                              authors=None, 
                              tags=None,
                              update_index=True)
        self.listing_pg.open_listing_rss_page('featured')
  
    def test_popular_listing__thumbs(self):
        #CREATE 5 REGULAR VIDEOS
        for x in range(5):
            vid_name = 'listing_test_'+str(x)
            self.create_video(name=vid_name,
                              watches=0,
                              update_index=True)
        #CREATE 30 POPULAR VIDEOS WITH NUM WATCHES THAT MATCH THE NUM in the VID NAME
        for x in range(11,41):
            vid_name = 'listing_test_'+str(x)
            self.create_video(name=vid_name,
                              watches=x*2, 
                              update_index=True)
        management.call_command('update_popularity')

        self.listing_pg.open_listing_page('popular')
        self.assertEqual(True, self.listing_pg.has_thumbnails())
        self.assertEqual(True, self.listing_pg.valid_thumbnail_sizes(140, 194))
        #POPULAR PAGE SHOULD BE LIMITED TO THE  15 MOST POPULAR VIDEOS
        self.assertEqual(True, self.listing_pg.thumbnail_count(15))

    def test_featured_listing__thumbs(self):
        self.listing_pg = listing_page.ListingPage(pcfwebqa)
        #CREATE 5 REGULAR VIDEOS
        for x in range(5):
            vid_name = 'listing_test_'+str(x)
            self.create_video(name=vid_name,
                              update_index=True)

        #CREATE VIDEOS THAT ARE FEATURED
        for x in range(16,21):
            vid_name = 'listing_test_'+str(x)
            self.create_video(name=vid_name, 
                              last_featured=datetime.datetime.now(), 
                              update_index=True)
        self.listing_pg.open_listing_page('featured')
        self.assertEqual(True, self.listing_pg.has_thumbnails())
        self.assertEqual(True, self.listing_pg.valid_thumbnail_sizes(140, 194))
        #Only the 5 Featured Videos should be displayed on the Page 
        self.assertEqual(True, self.listing_pg.thumbnail_count(5))


    def test_new_listing__title(self):
        """Verify videos listed have titles that are links to vid page.

        """
        title = 'webdriver test video'
        user = self.create_user(username='autotester', first_name='selene', last_name='driver')
        self.create_video(name=title,
                         description = 'This is the most awesome test video ever!',
                         user = user,
                         categories=[self.create_category(name='webdriver',
                                                             slug='webdriver')])
        self.listing_pg.open_listing_page('new')
        self.assertTrue(self.listing_pg.has_title(title))
        link = self.listing_pg.title_link(title)
        self.assertIn('webdriver-test-video', link)

    def test_listing__overlay(self):
        """Verify overlay appears on hover and has description text.
        """
        title = 'webdriver test video'
        description = 'This is the most awesome test video ever'
        self.create_video(name=title,
                         description = description,
                         )

        self.listing_pg.open_listing_page('new')

        has_overlay, overlay_description = self.listing_pg.has_overlay(title)
        self.assertTrue(has_overlay)
        self.assertIn(description, overlay_description)

    def test_listing__author(self):
        title = 'webdriver test video'
        description = 'This is the most awesome test video ever'
        user = self.create_user(username='autotester', first_name='webby', last_name='driver')
        self.create_video(name=title,
                         description = description,
                         authors=[3],
                         watches=1
                         )
        self.listing_pg.open_listing_page('popular')
        has_overlay, overlay_text = self.listing_pg.has_overlay(title)

        self.assertIn('webby driver', overlay_text)
        self.assertIn('/author/3/', overlay_text)


    def test_listing_new__page_name(self):
        self.listing_pg.open_listing_page('new')
        self.assertEqual('New Videos', self.listing_pg.page_name())


    def test_listing_new__page_rss(self):
        self.listing_pg.open_listing_page('new')
        feed_url = pcfwebqa.base_url + self.listing_pg._FEED_PAGE % 'new'
        self.assertEqual(feed_url, self.listing_pg.page_rss())

    def test_listing_popular__page_name(self):
        self.listing_pg.open_listing_page('popular')
        self.assertEqual('Popular Videos', self.listing_pg.page_name())


    def test_listing_popular__page_rss(self):
        self.listing_pg.open_listing_page('popular')
        feed_url = pcfwebqa.base_url + self.listing_pg._FEED_PAGE % 'popular'
        self.assertEqual(feed_url, self.listing_pg.page_rss())


    def test_listing_featured__page_name(self):
        self.listing_pg.open_listing_page('featured')
        self.assertEqual('Featured Videos', self.listing_pg.page_name())

    def test_listing_featured__page_rss(self):
        self.listing_pg.open_listing_page('featured')
        feed_url = pcfwebqa.base_url + self.listing_pg._FEED_PAGE % 'featured'
        self.assertEqual(feed_url, self.listing_pg.page_rss())

    def published(self, listing):
        """Verify videos display published date (if configured)."""
        assert False, 'this needs to be implemented'

