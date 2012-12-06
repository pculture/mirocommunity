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
from localtv.tests import BaseTestCase

from haystack import connections

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
            cls.create_video(name='b2', description='Foo bar a blender.'),
            cls.create_video(name='b3',
                             description='<h1>Foo</h1> <p>bar <span class="ro'
                             'cket">a blender</span></p>'),
            cls.create_video(name='b4', tags='blender'),
            cls.create_video(name='b5',
                          categories=[cls.create_category(name='Blender',
                                                           slug='tender')]),
            cls.create_video(name='b6', video_service_user='blender'),
            cls.create_video(name='b7',
                             feed=cls.create_feed('feed1', name='blender')),
        )
        cls.blender_users = (
            cls.create_user(username='blender'),
            cls.create_user(username='test1', first_name='Blender'),
            cls.create_user(username='test2', last_name='Blender'),
        )
        cls.blender_user_videos = ()
        for user in cls.blender_users:
            cls.blender_user_videos += (
                cls.create_video(name='b8u%s' % user.username, user=user),
                cls.create_video(name='b9a%s' % user.username, authors=[user])
            )

        cls.rocket_videos = (
            cls.create_video(name='Rocket'),
            cls.create_video(name='r2', description='Foo bar a rocket.'),
            cls.create_video(name='r3',
                             description='<h1>Foo</h1> <p>bar <span class="bl'
                             'ender">a rocket</span></p>'),
            cls.create_video(name='r4', tags='rocket'),
            cls.create_video(name='r5',
                             categories=[cls.create_category(name='Rocket',
                                                             slug='pocket')]),
            cls.create_video(name='r6', video_service_user='rocket'),
            cls.create_video(name='r7',
                             feed=cls.create_feed('feed2', name='rocket')),
        )
        cls.rocket_users = (
            cls.create_user(username='rocket'),
            cls.create_user(username='test3', first_name='Rocket'),
            cls.create_user(username='test4', last_name='Rocket'),
        )
        cls.rocket_user_videos = ()
        for user in cls.rocket_users:
            cls.rocket_user_videos += (
                cls.create_video(name='r8u%s' % user.username, user=user),
                cls.create_video(name='r9a%s' % user.username, authors=[user])
            )

        cls.search_videos = (
            cls.create_video(name='s1', search=cls.create_search("rogue")),
        )
        cls.playlist = cls.create_playlist(cls.blender_users[0])
        cls.playlist.add_video(cls.blender_videos[0])
        cls.playlist.add_video(cls.rocket_videos[0])

        cls.all_videos = set((cls.blender_videos + cls.blender_user_videos +
                              cls.rocket_videos + cls.rocket_user_videos +
                              cls.search_videos))
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
        results = dict((unicode(r.pk), r.object.name) for r in results)
        expected = dict((unicode(v.pk), v.name) for v in expected)

        result_pks = set(results.items())
        expected_pks = set(expected.items())
        self.assertEqual(result_pks, expected_pks)

    def test_search(self):
        """
        The basic query should return videos which contain the search term,
        even if there is HTML involved.

        """
        expected = self.blender_videos + self.blender_user_videos
        self.assertQueryResults("blender", expected)

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

    def test_search_exclude(self):
        """
        Search should exclude strings, phrases, and keywords preceded by a '-'

        We skip this test on Whoosh because it has a bug w.r.t exclusion:
        https://bitbucket.org/mchaput/whoosh/issue/254
        """
        if ('WhooshEngine' in
            connections['default'].options['ENGINE']):
            self.skipTest('Whoosh has bad handling of exclude queries')

        expected = (self.all_videos - set(self.blender_videos) -
                    set(self.blender_user_videos))
        self.assertQueryResults('-blender', expected)

        expected = (self.all_videos - set(self.blender_videos[1:3]) -
                    set(self.rocket_videos[1:3]))
        self.assertQueryResults('-"foo bar"', expected)

        expected = self.all_videos - set(self.blender_videos[6:7])
        self.assertQueryResults('-feed:blender', expected)

        expected = self.all_videos - set(self.blender_user_videos[:2])
        self.assertQueryResults('-user:blender', expected)

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

    def test_search_keyword__playlist(self):
        """
        Playlist keyword should search the videos' playlists, accepting a pk
        or a username/slug combination.

        """
        expected = self.blender_videos[:1] + self.rocket_videos[:1]
        self.assertQueryResults('playlist:blender/playlist', expected)
        self.assertQueryResults('playlist:1', expected)

    def test_search_keyword__search(self):
        """
        Search keyword should search the videos' related saved searches,
        accepting a pk or a query string.

        """
        expected = self.search_videos
        self.assertQueryResults('search:1', expected)
        self.assertQueryResults('search:rogue', expected)
        self.assertQueryResults('search:"rogue"', expected)

    def test_search_or(self):
        """
        Terms bracketed in {}s should be ORed together.

        """
        expected = (self.rocket_videos + self.rocket_user_videos +
                    self.blender_videos[1:3])
        self.assertQueryResults("{rocket foo}", expected)

        # For posterity, this test was added because of bz19056.
        expected = (self.rocket_videos + self.rocket_user_videos +
                    self.blender_user_videos[0:2])
        self.assertQueryResults("{user:blender rocket}", expected)

        # bz19083. Nonexistant keyword target in an or shouldn't freak out.
        expected = self.rocket_videos + self.rocket_user_videos
        self.assertQueryResults("{user:quandry rocket}", expected)

    def test_search_or_and(self):
        """
        Mixing OR and AND should work as expected.

        """
        expected = (self.create_video(name="EXTRA blender"),
                    self.create_video(name="EXTRA rocket"))

        self._rebuild_index()

        self.assertQueryResults('{rocket blender} extra', expected)
        self.assertQueryResults('extra {rocket blender}', expected)
