from localtv.tests import BaseTestCase

from localtv import search

class SearchTokenizeTestCase(BaseTestCase):
    """
    Tests for the search query tokenizer.
    """
    def assertTokenizes(self, query, result):
        self.assertEquals(tuple(search.tokenize(query)),
                          tuple(result))

    def test_split(self):
        """
        Space-separated tokens should be split apart.
        """
        self.assertTokenizes('foo bar baz', ('foo', 'bar', 'baz'))

    def test_quotes(self):
        """
        Quoted string should be kept together.
        """
        self.assertTokenizes('"foo bar" \'baz bum\'', ('foo bar', 'baz bum'))

    def test_negative(self):
        """
        Items prefixed with - should keep that prefix, even with quotes.
        """
        self.assertTokenizes('-foo -"bar baz"', ('-foo', '-bar baz'))

    def test_or_grouping(self):
        """
        {}s should group their keywords together.
        """
        self.assertTokenizes('{foo {bar baz} bum}', (['foo',
                                                      ['bar', 'baz'],
                                                      'bum'],))

    def test_colon(self):
        """
        :s should remain part of their word.
        """
        self.assertTokenizes('foo:bar', ('foo:bar',))

    def test_open_grouping(self):
        """
        An open grouping at the end should return all its items.
        """
        self.assertTokenizes('{foo bar', (['foo', 'bar'],))

    def test_open_quote(self):
        """
        An open quote should be stripped.
        """
        self.assertTokenizes('"foo', ('foo',))
        self.assertTokenizes("'foo", ('foo',))
