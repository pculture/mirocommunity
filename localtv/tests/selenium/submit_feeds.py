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


from localtv.tests.selenium.webdriver_base import WebdriverTestCase
from localtv.tests.selenium import pcfwebqa
from localtv.tests.selenium.front_pages import search_page, video_page, listing_page
from localtv.tests.selenium.admin_pages import manage_page
import time
from django.core import management


class SeleniumTestCaseSubmitVideoFeeds(WebdriverTestCase):

    def setUp(self):
        WebdriverTestCase.setUp(self)
        self.manage_pg = manage_page.ManagePage(pcfwebqa)
        self.listing_pg = listing_page.ListingPage(pcfwebqa)
        self.manage_pg.login(self.admin_user, self.admin_pass)


    def submit_feed(self, testcase):
        self.manage_pg.open_manage_page()
        kwargs = testcase
        self.manage_pg.submit_feed(**kwargs)
        self._update_index()


    def verify_video_page(self, testcase):
        search_pg = search_page.SearchPage(pcfwebqa)
        search_pg.on_searchable_page()
        kwargs =  testcase
        search_pg.search(kwargs['search'])
        result, page_url = search_pg.click_first_result()
        self.assertTrue(result, page_url)
        video_pg = video_page.VideoPage(pcfwebqa)
        video_metadata = video_pg.check_video_details(**kwargs)
        #check video details checks the displayed metadata and returns a list of errors if all the fields aren't there
        for results in video_metadata:
            self.assertFalse(results)

    def test_submit_feed__youtube_user(self):
        testcase = {'feed url': 'http://www.youtube.com/user/croatiadivers',
                    'title': 'Scuba Diving Croatia, Duiken Kroatie, Tauchen Kroatien',
                    'search': 'Duiken Kroatie', #term that returns a unique result
                    'tags': ['boat', 'cave', 'cavern', 'croatia', 'diving'],
                    'description': '5 Star PADI IDC Resort & BSAC Resort Centre. Vela Luka, Korcula, Croatia',
                    'source': 'croatiadivers'
                                     }
        
        self.submit_feed(testcase)
        self.verify_video_page(testcase)

    def test_submit_feed__blip(self):
        testcase = {'feed url': 'http://blip.tv/reelscience',
                    'feed name': 'Reel Science',
                    'title': 'Insects: Aliens on Earth',
                    'search': 'Insects: Aliens', #term that returns a unique result
                    'tags': ['learning', 'animation', 'alien', 'educational', 'humor'],
                    'description': 'Saw Prometheus? What if I told you there are creatures on Earth that are just as freaky?',
                    'source': 'Reel Science'
                                     }
        
        self.submit_feed(testcase)
        self.verify_video_page(testcase)

    def test_submit_feed__xml(self):
        testcase = {'feed url': 'http://qa.pculture.org/feeds_test/list-of-guide-feeds.xml',
                    'feed name': 'Static List',
                    'title': 'LandlineTV (HD)',
                    'search': 'LandlineTV', #term that returns a unique result
                    'description': 'Landline TV is sketch comedy that delivers witty, higher brow content about relevant pop culture and news events. Comically relevant... for about a week or so.',
                    'source': 'Static List'
                                     }
        self.submit_feed(testcase)
        self.verify_video_page(testcase)

    def test_submit_feed__vimeo(self):
        testcase = {'feed url': 'http://vimeo.com/jfinn/likes/rss',
                    'feed name': 'janet',
                    'title': 'WADDICT - Kiteskate Edit',
                    'search': 'Kiteskate',
                    'description': 'In addition to WADDICT part I & II, we have done an edit dedicated to kiteskating.',
                    'source': 'janet'
                                     }
        self.submit_feed(testcase)
        self.verify_video_page(testcase)


    def test_feed_listing_thumbnails__vimeo(self):
        testcase = {'feed url': 'http://vimeo.com/jfinn/likes/rss',
                    'feed name': 'janet',
                    'title': 'WADDICT - Kiteskate Edit',
                    'search': 'Kiteskate',
                    'description': 'In addition to WADDICT part I & II, we have done an edit dedicated to kiteskating.',
                    'source': 'janet'
                                     }
        self.submit_feed(testcase)
        self.manage_pg.click_feed_action(testcase['feed name'], "View")
        self.assertTrue(self.listing_pg.has_thumbnails())
        self.assertLess(self.listing_pg.default_thumbnail_percent(), 30)


    def test_submit_feed__dailymotion(self):
        testcase = {'feed url': 'http://www.dailymotion.com/rss/user/KEXP',
                    'feed name': 'KEXP',
                    'title': 'Centro-matic (Live at SXSW)',
                    'search': 'Centro-matic',
                    'description': 'Centro-matic perform live at the Brooklyn Vegan Free Day Party at Club DeVille during SXSW.',
                    'source': 'KEXP'
                                     }
        self.submit_feed(testcase)
        self.verify_video_page(testcase)


    def test_submit_feed__invalid(self):
        kwargs = {'feed url': 'http://www.dailymotion.com/relevance/search/vela+luka/1',
                  'feed source': 'invalid'
                 }
        self.manage_pg.open_manage_page()
        self.assertTrue(self.manage_pg.submit_feed(**kwargs))

    def test_submit_feed__update(self):
        kwargs = {'feed url': 'http://qa.pculture.org/feeds_test/feed9.rss',
                  'feed name': 'Feed update TEST',
                 }
        self.manage_pg.open_page('http://qa.participatoryculture.org/feeds_test/feed-add-items.php?i=1')
        self.manage_pg.open_manage_page()
        self.assertTrue(self.manage_pg.submit_feed(**kwargs))
        self._update_index()
        search_pg = search_page.SearchPage(pcfwebqa)
        search_pg.search('Feed update TEST')
        has_results, result = search_pg.has_results()
        self.assertTrue(result['titles']==1, result) 
        self.manage_pg.open_page('http://qa.participatoryculture.org/feeds_test/feed-add-items.php?i=2')
        management.call_command('update_sources')
        self._update_index()
        search_pg = search_page.SearchPage(pcfwebqa)
        search_pg.search('Feed update TEST')
        has_results, result = search_pg.has_results()
        self.assertTrue(result['titles']==13, result) 

        
        

      


    
    
        
