from localtv.tests.selenium import WebdriverTestCase
from localtv.tests.selenium.pages.front import search_page
from localtv.tests.selenium.pages.front import video_page
from localtv.tests.selenium.pages.front import listing_page
from localtv.tests.selenium.pages.admin import manage_page
from django.core import management

class SubmitVideoFeeds(WebdriverTestCase):
    """TestSuite for submitting video feeds to site. """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(SubmitVideoFeeds, cls).setUpClass()
        cls.manage_pg = manage_page.ManagePage(cls)
        cls.listing_pg = listing_page.ListingPage(cls)

        cls.create_user(username='admin',
                        password='password',
                        is_superuser=True)
        cls.listing_pg.open_page('')
        cls.listing_pg.log_in('admin', 'password')

    def setUp(self):
        super(SubmitVideoFeeds, self).setUp()
        management.call_command('update_index', interactive=False)



    def submit_feed(self, **kwargs):
        """Submit the video feed.

        """
        self.manage_pg.open_manage_page()
        self.manage_pg.submit_feed(**kwargs)
        self._update_index()

    def verify_video_page(self, **kwargs):
        """Search for a video from the feed, and verify metadata.

        """
        search_pg = search_page.SearchPage(self)
        search_pg.on_searchable_page()
        search_pg.search(kwargs['search'])
        result, page_url = search_pg.click_first_result()
        self.assertTrue(result, page_url)
        video_pg = video_page.VideoPage(self)
        video_metadata = video_pg.check_video_details(**kwargs)
        for results in video_metadata:
            self.assertFalse(results)

    def test_submit_feed__youtube_user(self):
        """Submit a youtube user feed.

        """
        kwargs = {
            'feed url': 'http://www.youtube.com/user/croatiadivers',
            'title': ('Scuba Diving Croatia, Duiken Kroatie, '
                      'Tauchen Kroatien'),
            'search': 'Duiken Kroatie',
            'tags': ['boat', 'cave', 'cavern', 'croatia', 'diving'],
            'description': ('5 Star PADI IDC Resort & BSAC Resort '
                            'Centre. Vela Luka, Korcula, Croatia'),
            'source': 'croatiadivers'
        }

        self.submit_feed(**kwargs)
        self.verify_video_page(**kwargs)

    def test_submit_feed__blip(self):
        """Submit a blip feed.

        """
        kwargs = {
            'feed url': 'http://blip.tv/reelscience',
            'feed name': 'Reel Science',
            'title': 'Insects: Aliens on Earth',
            'search': 'Insects: Aliens',
            'tags': ['learning', 'animation', 'alien',
                     'educational', 'humor'],
            'description': ('Saw Prometheus? What if I told you there '
                            'are creatures on Earth that are just as '
                            'freaky?'),
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
            'feed name': 'Videos janet likes on Vimeo',
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
        self.manage_pg.click_feed_action(kwargs['feed name'], "View")
        self.assertTrue(self.listing_pg.has_thumbnails())
        self.assertLess(self.listing_pg.default_thumbnail_percent(), 30)

    def test_submit_feed__dailymotion(self):
        """Submit a dailymotion feed.

        """
        kwargs = {
            'feed url': 'http://www.dailymotion.com/rss/user/KEXP',
            'feed name': 'KEXP',
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
            'feed name': 'Videos janet likes on Vimeo',
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
        search_pg = search_page.SearchPage(self)
        search_pg.search('Feed update TEST')
        _, result = search_pg.has_results()
        self.assertTrue(result['titles'] == 1, result)
        self.manage_pg.open_page('http://qa.pculture.org/feeds_test/'
                                 'feed-add-items.php?i=2')
        management.call_command('update_sources')
        search_pg = search_page.SearchPage(self)
        search_pg.search('Feed update TEST')
        _, result = search_pg.has_results()
        self.assertTrue(result['titles'] == 13, result)
