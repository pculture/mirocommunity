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


from localtv.tests.selenium import WebdriverTestCase

from localtv.tests.selenium.pages.front import search_page


class VideoSearch(WebdriverTestCase):
    """Test various search terms return expected results.

    """
    test_feeds = {'youtube user': {
                  'feed url': ('http://gdata.youtube.com/feeds/api/users/'
                               '4001v63/uploads'),
                  'feed name': '4001v63',
                  'feed author': '4001v63',
                  'feed source': 'Youtube User',
                  'approve all': True,
                  },
                  }
    search_terms = {'multi words with symbol': 'Duo Orre & Sinisalo',
                    'non-ascii-char': u'Elämäkerta',
                    'single word': 'Duo',
                    'numerical': '2009'
                    }

    def setUp(self):
        WebdriverTestCase.setUp(self)

    def test_search_title__phrase(self):
        """Search for a phrase.

        """
        term = 'Duo Orre & Sinisalo'
        self.create_video(term)
        search_pg = search_page.SearchPage(self)
        search_pg.search(term)
        has_results, result = search_pg.has_results()
        self.assertTrue(has_results, result)

    def test_search_title__non_ascii(self):
        """Search with non-ascii chars in term.

        """
        term = u'Elämäkerta'
        self.create_video(term)
        search_pg = search_page.SearchPage(self)
        search_pg.search(term)
        has_results, result = search_pg.has_results()
        self.assertTrue(has_results, result)

    def test_search_title__numerical(self):
        """Search numerical phrase.

        """
        term = '2009'
        self.create_video(term)
        search_pg = search_page.SearchPage(self)
        search_pg.search(term)
        has_results, result = search_pg.has_results()
        self.assertTrue(has_results, result)

    def test_search_title__single_word(self):
        """Search 3-letter work in title.

        """

        term = 'Duo'
        self.create_video(term)
        search_pg = search_page.SearchPage(self)
        search_pg.search(term)
        has_results, result = search_pg.has_results()
        self.assertTrue(has_results, result)

    def test_search_title__negated_term(self):
        """Search a negated term
        """

        term = 'Duo'
        self.create_video(term)
        self.create_video(term)
        search_pg = search_page.SearchPage(self)
        search_pg.search('-' + term)
        has_results, result = search_pg.has_results(expected=False)
        self.assertFalse(has_results, result)

    def test_search_title__or_terms(self):
        """Search multiple terms

        """
        term1 = 'Sinisalo'
        term2 = u'Elämäkerta'
        self.create_video(term1)
        self.create_video(term2)
        search_pg = search_page.SearchPage(self)
        search_term = " ".join(['{', term2, term1, '}'])
        search_pg.search(search_term)
        has_results, result = search_pg.has_results()
        self.assertTrue(result['titles'] == 2, result)

    def test_search__num_results(self):
        """Check expected number of results returned.

        """
        titles = ['Duo Orre & Sinisalo', 'Duo', 'Dual', 'monkeys']
        for title in titles:
            self.create_video(title)
        search_pg = search_page.SearchPage(self)
        search_term = 'Duo'
        search_pg.search(search_term)
        _, result = search_pg.has_results()
        self.assertEqual(result['titles'], 2, result)
