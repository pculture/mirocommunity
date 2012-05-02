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

from localtv.search.query import SmartSearchQuerySet
from localtv.tests.base import BaseTestCase


class TokenizeTestCase(BaseTestCase):
    """
    Tests for the search query tokenizer.

    """
    def assertTokenizes(self, query, result):
        self.assertEqual(tuple(SmartSearchQuerySet().tokenize(query)),
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

    def test_unicode(self):
        """
        Unicode should be handled as regular characters.

        """
        self.assertTokenizes(u'espa\xf1a', (u'espa\xf1a',))

    def test_unicode_not_latin_1(self):
        """
        Non latin-1 characters should be included.

        """
        self.assertTokenizes(u'foo\u1234bar', (u'foo\u1234bar',))

    def test_blank(self):
        """
        A blank query should tokenize to a blank list.

        """
        self.assertTokenizes('', ())


class AutoQueryTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(AutoQueryTestCase, cls).setUpClass()
        cls._start_test_transaction()
        cls._disable_index_updates()
        cls.blender_videos = (
            cls.create_video(name='Blender'),
            cls.create_video(description='Foo bar a blender.'),
            cls.create_video(description='<h1>Foo</h1> <p>bar <span class="ro'
                                          'cket">a blender</span></p>'),
            cls.create_video(tags='blender'),
            cls.create_video(
                          categories=[cls.create_category(name='Blender',
                                                           slug='tender')]),
            cls.create_video(video_service_user='blender'),
            cls.create_video(feed=cls.create_feed('feed1', name='blender')),
        )
        cls.blender_users = (
            cls.create_user(username='blender'),
            cls.create_user(username='test1', first_name='Blender'),
            cls.create_user(username='test2', last_name='Blender'),
        )
        cls.blender_user_videos = ()
        for user in cls.blender_users:
            cls.blender_user_videos += (
                cls.create_video(user=user),
                cls.create_video(authors=[user])
            )

        cls.rocket_videos = (
            cls.create_video(name='Rocket'),
            cls.create_video(description='Foo bar a rocket.'),
            cls.create_video(description='<h1>Foo</h1> <p>bar <span class="bl'
                                          'ender">a rocket</span></p>'),
            cls.create_video(tags='rocket'),
            cls.create_video(
                          categories=[cls.create_category(name='Rocket',
                                                           slug='pocket')]),
            cls.create_video(video_service_user='rocket'),
            cls.create_video(feed=cls.create_feed('feed2', name='rocket')),
        )
        cls.rocket_users = (
            cls.create_user(username='rocket'),
            cls.create_user(username='test3', first_name='Rocket'),
            cls.create_user(username='test4', last_name='Rocket'),
        )
        cls.rocket_user_videos = ()
        for user in cls.rocket_users:
            cls.rocket_user_videos += (
                cls.create_video(user=user),
                cls.create_video(authors=[user])
            )

        cls.all_videos = (cls.blender_videos + cls.blender_user_videos +
                           cls.rocket_videos + cls.rocket_user_videos)
        cls._enable_index_updates()
        cls._rebuild_index()

    @classmethod
    def tearDownClass(cls):
        super(AutoQueryTestCase, cls).tearDownClass()
        cls._clear_index()
        cls._end_test_transaction()

    def _fixture_setup(self):
        pass

    def _fixture_teardown(self):
        pass

    def assertQueryResults(self, query, expected):
        """
        Given a query and a list of videos, checks that all expected videos
        are found by a search with the given query.

        """
        results = SmartSearchQuerySet().auto_query(query)
        result_pks = set([unicode(r.pk) for r in results])
        expected = dict((unicode(v.pk), v) for v in expected)

        self.assertEqual(result_pks, set(expected))

    def test_search(self):
        """
        The basic query should return videos which contain the search term,
        even if there is HTML involved.

        """
        expected = self.blender_videos + self.blender_user_videos

    def test_search_phrase(self):
        """
        Phrases in quotes should be searched for as a phrase.

        """
        expected = self.blender_videos[1:3] + self.rocket_videos[1:3]
        self.assertQueryResults('"foo bar"', expected)

    def test_search_blank(self):
        """
        Searching for a blank string should be handled gracefully.
        """
        self.assertQueryResults('', self.all_videos)

    def test_search_keyword__tag(self):
        """
        Tag keyword should only search the videos' tags.

        """
        self.assertQueryResults('tag:blender', self.blender_videos[3:4])

    def test_search_keyword__category(self):
        """
        Category keyword should search the videos' categories, accepting name,
        slug, and pk.

        """
        expected = self.blender_videos[4:5]
        self.assertQueryResults('category:blender', expected)
        self.assertQueryResults('category:tender', expected)
        self.assertQueryResults('category:1', expected)

    def test_search_keyword__user(self):
        """
        User keyword should accept username or pk, and should check user and
        authors.

        """
        expected = self.blender_user_videos[0:2]
        self.assertQueryResults('user:Blender', expected)
        self.assertQueryResults('user:1', expected)

    def test_search_keyword__feed(self):
        """
        Feed keyword should search the videos' feeds, accepting feed name or
        pk.

        """
        expected = self.blender_videos[6:7]
        self.assertQueryResults('feed:Blender', expected)
        self.assertQueryResults('feed:1', expected)
