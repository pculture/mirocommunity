from nose.tools import assert_false
from localtv.tests.selenium import WebdriverTestCase
from localtv.tests.selenium.pages.front import submit_page
from localtv.tests.selenium.pages.front import video_page


class SubmitVideo(WebdriverTestCase):
    """TestSuite for submitting videos to site. """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(SubmitVideo, cls).setUpClass()
        cls.video_pg = video_page.VideoPage(cls)
        cls.submit_pg = submit_page.SubmitPage(cls)

        cls.test_videos = {
            'youtube': {
                'url': 'http://www.youtube.com/watch?v=WqJineyEszo',
                'form': 'scraped',
                'title': 'X Factor Audition - Stop Looking At My Mom',
                'search': 'stop looking at my mom rap',
                'tags': ['competition', 'mom', 'music', 'rap'],
                'description': ('Brian Bradley sings his original song '
                                'Stop Looking'),
                'source': 'clowntownhonkhonk',
            },
            'youtube duplicate': {
                'url': 'http://www.youtube.com/watch?v=WqJineyEszo',
                'form': 'duplicate',
                'title': 'X Factor Audition - Stop Looking At My Mom',
                'search': 'stop looking at my mom rap',
                'tags': ['competition', 'mom', 'music', 'rap'],
                'description': ('Brian Bradley sings his original song '
                                'Stop Looking'),
                'source': 'clowntownhonkhonk',
            },
            'vimeo': {
                'url': 'http://vimeo.com/42231616/',
                'form': 'scraped',
                'title': 'WADDICT - Kiteskate Edit',
                'search': 'kiteskate',
                'tags': ['kitesurf', 'kiteskate', 'wakeskate',
                          'western australia', 'safety bay',
                          'cabrinha', 'kitaddict'],
                'description': ('In addition to WADDICT part I & II, '
                                'we have done an edit dedicated to '
                                'kiteskating.'),
                'source': 'spocky',
                'thumb_url': ('http://b.vimeocdn.com/ts/292/946/'
                              '292946977_200.jpg')
            },
            'blip': {
                'url': ('http://blip.tv/sarchons-invade-the-movies/'
                        'sarchons-invade-the-movies-rock-of-ages-2012'
                        '-movie-review-6208658'),
                'form': 'scraped',
                'title': ('ROCK OF AGES (2012) MOVIE REVIEW by '
                          'SARCHONS INVADE THE MOVIES'),
                'search': 'sarchons invade the movies',
                'tags': ['movie review', 'comedy', 'animation',
                         'diego boneta', 'rock of ages'],
                'source': 'sarchons',
                'description': ('Arn-0 & 0-Nad take a voyage back in '
                                'time to 1987 to the famous Sunset '
                                'Strip in Los Angeles'),
            },
            'amara direct detect': {
                'url': ('http://qa.pculture.org/feeds_test/'
                        'short-video.ogv'),
                'form': 'direct',
                'title': 'Short Video with Amara Widget',
                'thumb_url': ('http://qa.pculture.org/feeds_test/'
                              'orim_avatar.png'),
                'description': ('test video that exists on '
                                'universalsubtitels.org with '
                                'amara widget is automatically '
                                'detected'),
            }
        }

    def setUp(self):
        super(SubmitVideo, self).setUp()
        self._clear_index()
        self.create_user(username='admin',
                         password='password',
                         is_superuser=True)
        self.submit_pg.log_in('admin', 'password')

    def verify_video_submit(self, testcase):
        """Open the video page and verify the metadata.

        """
        kwargs = self.test_videos[testcase]
        video_page_url = self.submit_pg.submit_a_valid_video(**kwargs)
        self.video_pg.open_page(video_page_url + "/")
        video_metadata = self.video_pg.check_video_details(**kwargs)
        for results in video_metadata:
            assert_false(results)

    def test_submit__youtube(self):
        """Submit a youtube video.

        """
        testcase = 'youtube'
        self.verify_video_submit(testcase)
        self.assertTrue(self.video_pg.verify_amara_widget())

    def test_submit__vimeo(self):
        """Submit a vimeo video.

        """
        testcase = 'vimeo'
        self.verify_video_submit(testcase)
        self.assertTrue(self.video_pg.verify_amara_widget())

    def test_submit__blip(self):
        """Submit a blip video.

        """
        testcase = 'blip'
        self.verify_video_submit(testcase)

    def test_submit__amara_video_direct(self):
        """Submit a video on amara site.

           This should have the amara widget present.
        """
        testcase = 'amara direct detect'
        self.verify_video_submit(testcase)
        self.assertTrue(self.video_pg.verify_amara_widget())

    def test_submit__duplicate(self):
        """Submit a duplicate video.

        """
        kwargs = self.test_videos['youtube']
        self.submit_pg.submit_a_valid_video(**kwargs)
        self.verify_video_submit('youtube duplicate')
        self.assertTrue(self.video_pg.verify_amara_widget())
