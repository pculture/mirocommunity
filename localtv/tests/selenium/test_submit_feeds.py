from localtv.tests.selenium import WebdriverTestCase
from localtv.tests.selenium.pages.front import search_page
from localtv.tests.selenium.pages.front import listing_page
from localtv.tests.selenium.pages.admin import manage_page
from django.core import management
import time


class SubmitVideoFeeds(WebdriverTestCase):
    """TestSuite for submitting video feeds to site. """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(SubmitVideoFeeds, cls).setUpClass()
        cls.manage_pg = manage_page.ManagePage(cls)
        cls.listing_pg = listing_page.ListingPage(cls)
        cls.search_pg = search_page.SearchPage(cls)
        cls.create_user(username='feedadmin',
                        password='password',
                        is_superuser=True)
        cls.listing_pg.open_page(cls.base_url[:-1])
        cls.listing_pg.log_in('feedadmin', 'password')

    def setUp(self):
        super(SubmitVideoFeeds, self).setUp()
        self._clear_index()

    def submit_feed(self, **kwargs):
        """Submit the video feed.

        """
        self.manage_pg.open_manage_page()
        self.manage_pg.submit_feed(**kwargs)

    def verify_video_page(self, **kwargs):
        """Search for a video from the feed, and verify metadata.

        """
        self.manage_pg.click_feed_action(kwargs['feed name'], 'View')
        if self.manage_pg.is_element_present('div.message'):
            time.sleep(4)
            self.manage_pg.page_refresh()
        self.assertTrue(self.listing_pg.has_thumbnails())

    def test_submit_feed__youtube_user(self):
        """Submit a youtube user feed.

        """
        kwargs = {
            'feed url': 'http://www.youtube.com/user/janetefinn',
            'feed name': 'Uploads by Janet Dragojevic',
            'source': 'Janet Dragojevic'
        }

        self.submit_feed(**kwargs)
        self.verify_video_page(**kwargs)

    def test_submit_feed__blip(self):
        """Submit a blip feed.

        """
        kwargs = {
            'feed url': 'http://blip.tv/reelscience',
            'feed name': 'Reel Science',
            'source': 'reelscience'
        }

        self.submit_feed(**kwargs)
        self.verify_video_page(**kwargs)

    def test_submit_feed__xml(self):
        """Submit a regular xml feed.

        """
        kwargs = {
            'feed url': ('http://qa.pculture.org/feeds_test/'
                         'list-of-guide-feeds.xml'),
            'feed name': 'Static List',
            'title': 'LandlineTV (HD)',
            # term that returns a unique result
            'search': 'LandlineTV',
            'description': ('Landline TV is sketch comedy that '
                            'delivers witty, higher brow content '
                            'about relevant pop culture and news '
                            'events. Comically relevant... for '
                            'about a week or so.'),
            'source': 'Static List'
        }
        self.submit_feed(**kwargs)
        self.verify_video_page(**kwargs)

    def test_submit_feed__vimeo(self):
        """Submit a vimeo feed.

        """
        kwargs = {
            'feed url': 'http://vimeo.com/jfinn/likes/rss',
            'feed name': 'Videos janet likes',
            'title': 'WADDICT - Kiteskate Edit',
            'search': 'Kiteskate',
            'description': ('In addition to WADDICT part I & II, '
                            'we have done an edit dedicated to '
                            'kiteskating.'),
            'source': 'spocky'
        }
        self.submit_feed(**kwargs)
        self.verify_video_page(**kwargs)

    def test_feed_thumbnails__vimeo(self):
        """Verify submitted vimeo feed has thumbnails.

        """
        kwargs = {
            'feed url': 'http://vimeo.com/user8568767/videos/rss',
            'feed name': "Andrea Schneider's videos",
            'source': 'user8568767'
        }
        self.submit_feed(**kwargs)
        self.manage_pg.click_feed_action(kwargs['feed name'], "View")
        self.assertTrue(self.listing_pg.has_thumbnails())
        self.assertLess(self.listing_pg.default_thumbnail_percent(), 30)

    def test_submit_feed__dailymotion(self):
        """Submit a dailymotion feed.

        """
        kwargs = {
            'feed url': 'http://www.dailymotion.com/rss/user/KEXP',
            'feed name': 'KEXP - Most recent videos - Dailymotion',
            'title': 'Centro-matic (Live at SXSW)',
            'search': 'Centro-matic',
            'description': ('Centro-matic perform live at the '
                            'Brooklyn Vegan Free Day Party at '
                            'Club DeVille during SXSW.'),
            'source': 'KEXP'
        }
        self.submit_feed(**kwargs)
        self.verify_video_page(**kwargs)

    def test_submit_feed__duplicate(self):
        """Submit a duplicate feed url.

        """
        kwargs = {
            'feed url': 'http://vimeo.com/jfinn/likes/rss',
            'feed name': 'Videos janet likes',
            'title': 'WADDICT - Kiteskate Edit',
            'search': 'Kiteskate',
            'description': ('In addition to WADDICT part I & II, '
                            'we have done an edit dedicated to '
                            'kiteskating.'),
            'source': 'spocky'
        }
        self.submit_feed(**kwargs)

        kwargs['feed source'] = 'duplicate'
        self.manage_pg.open_manage_page()
        self.assertTrue(self.manage_pg.submit_feed(**kwargs))

    def test_submit_feed__update(self):
        """Verify videos are updated when feed updates.

        """
        kwargs = {'feed url': 'http://qa.pculture.org/feeds_test/'
                              'feed9.rss',
                  'feed name': 'Feed update TEST',
                  }
        self.manage_pg.open_page('http://qa.pculture.org/feeds_test/'
                                 'feed-add-items.php?i=1')
        self.manage_pg.open_manage_page()
        self.manage_pg.submit_feed(**kwargs)
        self.search_pg = search_page.SearchPage(self)
        self.search_pg.search('Feed update TEST')
        _, result = self.search_pg.has_results()
        self.assertTrue(result['titles'] == 1, result)
        self.manage_pg.open_page('http://qa.pculture.org/feeds_test/'
                                 'feed-add-items.php?i=2')
        management.call_command('update_sources')

        self.search_pg = search_page.SearchPage(self)
        self.search_pg.search('Feed update TEST')
        _, result = self.search_pg.has_results()
        self.assertTrue(result['titles'] == 13, result)
