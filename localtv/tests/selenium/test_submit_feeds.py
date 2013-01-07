#-*- coding: utf-8 -*-
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
from localtv.tests.selenium.pages.front import search_page
from localtv.tests.selenium.pages.front import video_page
from localtv.tests.selenium.pages.front import listing_page
from localtv.tests.selenium.pages.admin import manage_page
from django.core import management


class SubmitVideoFeeds(WebdriverTestCase):
    """Test the submission of supported and unsupported feeds.

    """

    def setUp(self):
        WebdriverTestCase.setUp(self)
        self.manage_pg = manage_page.ManagePage(self)
        self.listing_pg = listing_page.ListingPage(self)
        self.manage_pg.login(self.admin_user, self.admin_pass)

    def submit_feed(self, testcase):
        """Submit the video feed.

        """
        self.manage_pg.open_manage_page()
        kwargs = testcase
        self.manage_pg.submit_feed(**kwargs)
        self._update_index()

    def verify_video_page(self, testcase):
        """Search for a video from the feed, and verify metadata.

        """
        search_pg = search_page.SearchPage(self)
        search_pg.on_searchable_page()
        kwargs = testcase
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
        testcase = {'feed url': 'http://www.youtube.com/user/croatiadivers',
                    'title': ('Scuba Diving Croatia, Duiken Kroatie, '
                              'Tauchen Kroatien'),
                    'search': 'Duiken Kroatie',
                    'tags': ['boat', 'cave', 'cavern', 'croatia', 'diving'],
                    'description': ('5 Star PADI IDC Resort & BSAC Resort '
                                    'Centre. Vela Luka, Korcula, Croatia'),
                    'source': 'croatiadivers'
                    }

        self.submit_feed(testcase)
        self.verify_video_page(testcase)

    def test_submit_feed__blip(self):
        """Submit a blip feed.

        """
        testcase = {'feed url': 'http://blip.tv/reelscience',
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

        self.submit_feed(testcase)
        self.verify_video_page(testcase)

    def test_submit_feed__xml(self):
        """Submit a regular xml feed.

        """
        testcase = {'feed url': ('http://qa.pculture.org/feeds_test/'
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
        self.submit_feed(testcase)
        self.verify_video_page(testcase)

    def test_submit_feed__vimeo(self):
        """Submit a vimeo feed.

        """
        testcase = {'feed url': 'http://vimeo.com/jfinn/likes/rss',
                    'feed name': 'Videos janet likes on Vimeo',
                    'title': 'WADDICT - Kiteskate Edit',
                    'search': 'Kiteskate',
                    'description': ('In addition to WADDICT part I & II, '
                                    'we have done an edit dedicated to '
                                    'kiteskating.'),
                    'source': 'spocky'
                    }
        self.submit_feed(testcase)
        self.verify_video_page(testcase)

    def test_feed_thumbnails__vimeo(self):
        """Verify submitted vimeo feed has thumbnails.

        """
        testcase = {'feed url': 'http://vimeo.com/jfinn/likes/rss',
                    'feed name': 'Videos janet likes on Vimeo',
                    'title': 'WADDICT - Kiteskate Edit',
                    'search': 'Kiteskate',
                    'description': ('In addition to WADDICT part I & II, '
                                    'we have done an edit dedicated to '
                                    'kiteskating.'),
                    'source': 'spocky'
                    }
        self.submit_feed(testcase)
        self.manage_pg.click_feed_action(testcase['feed name'], "View")
        self.assertTrue(self.listing_pg.has_thumbnails())
        self.assertLess(self.listing_pg.default_thumbnail_percent(), 30)

    def test_submit_feed__dailymotion(self):
        """Submit a dailymotion feed.

        """
        testcase = {'feed url': 'http://www.dailymotion.com/rss/user/KEXP',
                    'feed name': 'KEXP',
                    'title': 'Centro-matic (Live at SXSW)',
                    'search': 'Centro-matic',
                    'description': ('Centro-matic perform live at the '
                                    'Brooklyn Vegan Free Day Party at '
                                    'Club DeVille during SXSW.'),
                    'source': 'KEXP'
                    }
        self.submit_feed(testcase)
        self.verify_video_page(testcase)

    def test_submit_feed__duplicate(self):
        """Submit a duplicate feed url.

        """
        testcase = {'feed url': 'http://vimeo.com/jfinn/likes/rss',
                    'feed name': 'Videos janet likes on Vimeo',
                    'title': 'WADDICT - Kiteskate Edit',
                    'search': 'Kiteskate',
                    'description': ('In addition to WADDICT part I & II, '
                                    'we have done an edit dedicated to '
                                    'kiteskating.'),
                    'source': 'spocky'
                    }
        self.submit_feed(testcase)

        testcase['feed source'] = 'duplicate'
        self.manage_pg.open_manage_page()
        self.assertTrue(self.manage_pg.submit_feed(**testcase))

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
