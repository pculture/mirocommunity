"""
Miro Community - Easiest way to make a video website

Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation

Miro Community is free software: you can redistribute it and/or modify it
under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

Miro Community is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.
"""

from nose.tools import assert_false
from localtv.tests.selenium import WebdriverTestCase
from localtv.tests.selenium.pages.front import submit_page
from localtv.tests.selenium.pages.front import video_page
from localtv.tests.selenium.pages.front import user_nav


class SubmitVideo(WebdriverTestCase):

    test_videos = {'youtube': {
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
                       'title': ('ROCK OF AGES (2012) MOVIE REVIEW by SARCHONS '
                                 'INVADE THE MOVIES'),
                       'search': 'sarchons invade the movies',
                       'tags': ['movie review', 'comedy', 'animation', 
                                'diego boneta', 'rock of ages'],
                       'source': 'sarchons',
                       'description': ('Arn-0 & 0-Nad take a voyage back in '
                                       'time to 1987 to the famous Sunset '
                                       'Strip in Los Angeles'),
                   },

                   'amara embed code': {
                       'url': ('http://www.universalsubtitles.org/en/videos/'
                               'zrd5s48bQYg6/info/what-is-a-flame/'),
                       'form': 'embed',
                       'title': 'What is a Flame',
                       'thumb_url': ('http://s3.amazonaws.com/s3.userdata.www.'
                                     'universalsubtitles.org/video/thumbnail/'
                                     '761aa7b2e5981b228460a8626b8b424ca3f75b31'
                                     '_jpg_120x90'
                                     '_crop-smart_upscale-True_q85.jpg'),
                       'search': 'Flame Challange',
                       'description': ('Although this Flame Challenge entry '
                                       'was first submitted on Vimeo, this '
                                       'goes out to all the YouTube viewers'
                                       'out there. Thanks to Alan Alda and The '
                                       'Center for Communicating Science for '
                                       'creating such an educational and '
                                       'creative venue!'),
                       'tags': 'educational',
                       'embed': ('<script type="text/javascript'
                                 'src="http://s3.amazonaws.com/'
                                 's3.www.universalsubtitles.org/embed.js">'
                                 '({"video_url": "http://www.youtube.com/'
                                 'watch?v=5ymAXKXhvHI"})'
                                 '</script>'),
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
        WebdriverTestCase.setUp(self)
        nav_pg = user_nav.NavPage(self)
        nav_pg.login(self.admin_user, self.admin_pass)
        self.video_pg = video_page.VideoPage(self)
        self.submit_pg = submit_page.SubmitPage(self)

    def verify_video_submit(self, testcase):
        """Open the video page and verify the metadata.

        """
        kwargs = self.test_videos[testcase]
        video_page_url = self.submit_pg.submit_a_valid_video(**kwargs)
        self.video_pg.open_page(video_page_url)
        video_metadata = self.video_pg.check_video_details(**kwargs)
        for results in video_metadata:
            assert_false(results)

    def test_submit__youtube(self):
        """Submit a youtube video.

        """
        testcase = 'youtube'
        self.verify_video_submit(testcase)

    def test_submit__vimeo(self):
        """Submit a vimeo video.

        """
        testcase = 'vimeo'
        self.verify_video_submit(testcase)

    def test_submit__blip(self):
        """Submit a blip video.

        """
        testcase = 'blip'
        self.verify_video_submit(testcase)

    def test_submit__amara_embed(self):
        """Submit a video with amara embed code.

        """
        testcase = 'amara embed code'
        self.verify_video_submit(testcase)
        self.video_pg.verify_amara_widget()

    def test_submit__amara_video_direct(self):
        """Submit a video on amara site.

           This should have the amara widget present.
        """
        testcase = 'amara direct detect'
        self.verify_video_submit(testcase)
        self.video_pg.verify_amara_widget()

    def test_submit__duplicate(self):
        """Submit a duplicate video.

        """
        kwargs = self.test_videos['youtube']
        self.submit_pg.submit_a_valid_video(**kwargs)
        self.verify_video_submit('youtube duplicate')
