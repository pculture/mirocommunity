# -*- coding: utf-8 -*-
from localtv.tests.selenium import WebdriverTestCase

from localtv.tests.selenium.pages.front import search_page


class VideoSearch(WebdriverTestCase):
    """TestSuite for site video searches.  """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(VideoSearch, cls).setUpClass()
        cls.search_pg = search_page.SearchPage(cls)

    def setUp(self):
        super(VideoSearch, self).setUp()
        self._clear_index()

    def test_search_title__phrase(self):
        """Search for a phrase.

        """
        term = 'Duo Orre & Sinisalo'
        self.create_video(term)
        self.search_pg.search(term)
        has_results, result = self.search_pg.has_results()
        self.assertTrue(has_results, result)

    def test_search_title__non_ascii(self):
        """Search with non-ascii chars in term.

        """
        term = u'Elämäkerta'
        self.create_video(term)
        self.search_pg.search(term)
        has_results, result = self.search_pg.has_results()
        self.assertTrue(has_results, result)

    def test_search_title__numerical(self):
        """Search numerical phrase.

        """
        term = '2009'
        self.create_video(term)
        self.search_pg.search(term)
        has_results, result = self.search_pg.has_results()
        self.assertTrue(has_results, result)

    def test_search_title__single_word(self):
        """Search 3-letter work in title.

        """

        term = 'Duo'
        self.create_video(term)
        self.search_pg.search(term)
        has_results, result = self.search_pg.has_results()
        self.assertTrue(has_results, result)

    def test_search_title__negated_term(self):
        """Search a negated term
        """

        term = 'Duo'
        self.create_video(term)
        self.create_video(term)
        self.search_pg.search('-' + term)
        has_results, result = self.search_pg.has_results(expected=False)
        self.assertFalse(has_results, result)

    def test_search_title__or_terms(self):
        """Search multiple terms

        """
        term1 = 'Sinisalo'
        term2 = u'Elämäkerta'
        self.create_video(term1)
        self.create_video(term2)
        search_term = " ".join(['{', term2, term1, '}'])
        self.search_pg.search(search_term)
        has_results, result = self.search_pg.has_results()
        self.assertTrue(result['titles'] == 2, result)

    def test_search__num_results(self):
        """Check expected number of results returned.

        """
        titles = ['Duo Orre & Sinisalo', 'Duo', 'Dual', 'monkeys']
        for title in titles:
            self.create_video(title)
        search_term = 'Duo'
        self.search_pg.search(search_term)
        _, result = self.search_pg.has_results()
        self.assertEqual(result['titles'], 2, result)
