# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
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

from django.contrib.auth.models import User

from localtv.tests import BaseTestCase

from localtv import search
from localtv.models import Video, SavedSearch, Feed
from localtv.playlists.models import Playlist

class SearchTokenizeTestCase(BaseTestCase):
    """
    Tests for the search query tokenizer.
    """
    def assertTokenizes(self, query, result):
        self.assertEqual(tuple(search.tokenize(query)),
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

    fixtures = BaseTestCase.fixtures + ['categories', 'feeds', 'savedsearches',
                                        'videos']

    def _rebuild_index(self):
        """
        Rebuilds the search index.
        """
        from haystack import site
        index = site.get_index(Video)
        index.reindex()

    def search(self, query):
        return [result.object for result in search.auto_query(query)]

    def test_search(self):
        """
        The basic query should return videos which contain the search term.
        """
        self._rebuild_index()
        results = search.auto_query('blender')
        self.assertTrue(results)
        for result in results:
            self.assertTrue('blender' in result.text.lower(), result.text)

    def test_search_description_with_html(self):
        """
        If the description contains HTML, searching should still find words
        next to HTML tags.
        """
        self._rebuild_index()
        results = search.auto_query('blahblah')
        self.assertTrue(results)

    def test_search_phrase(self):
        """
        Phrases in quotes should be searched for as a phrase.
        """
        self._rebuild_index()
        results = search.auto_query('"empty mapping"')
        self.assertTrue(results)
        for result in results:
            self.assertTrue('empty mapping' in result.text.lower())

    def test_search_includes_tags(self):
        """
        Search should search the tags for videos.
        """
        video = Video.objects.get(pk=20)
        video.tags = 'tag1 tag2'
        video.save()

        self._rebuild_index()

        self.assertEqual(self.search('tag1'), [video])
        self.assertEqual(self.search('tag2'), [video])
        self.assertEqual(self.search('tag2 tag1'), [video])

        self.assertEqual(self.search('tag:tag1'), [video])
        self.assertEqual(self.search('tag:tag2'), [video])
        self.assertEqual(self.search('tag:tag2 tag:tag1'), [video])

    def test_search_includes_categories(self):
        """
        Search should search the category for videos.
        """
        video = Video.objects.get(pk=20)
        video.categories = [1, 2] # Miro, Linux
        video.save()

        self._rebuild_index()

        self.assertEqual(self.search('Miro'), [video])
        self.assertEqual(self.search('Linux'), [video])
        self.assertEqual(self.search('Miro Linux'), [video])

        self.assertEqual(self.search('category:Miro'), [video]) # name
        self.assertEqual(self.search('category:linux'), [video]) # slug
        self.assertEqual(self.search('category:1 category:2'), [video]) # pk

    def test_search_includes_user(self):
        """
        Search should search the user who submitted videos.
        """
        video = Video.objects.get(pk=20)
        video.user = User.objects.get(username='superuser')
        video.user.username = 'SuperUser'
        video.user.first_name = 'firstname'
        video.user.last_name = 'lastname'
        video.user.save()
        video.save()

        video2 = Video.objects.get(pk=47)
        video2.authors = [video.user]
        video2.save()

        self._rebuild_index()

        self.assertEqual(self.search('superuser'), [video2, video])
        self.assertEqual(self.search('firstname'), [video2, video])
        self.assertEqual(self.search('lastname'), [video2, video])

        self.assertEqual(self.search('user:SuperUser'),
                          [video2, video]) # name
        self.assertEqual(self.search('user:superuser'),
                          [video2, video]) # case-insenstive name
        self.assertEqual(self.search('user:%i' % video.user.pk),
                          [video2, video]) # pk

    def test_search_excludes_user(self):
        """
        -user:name should exclude that user's videos from the search results.
        """
        video = Video.objects.get(pk=20)
        video.user = User.objects.get(username='superuser')
        video.user.username = 'SuperUser'
        video.user.first_name = 'firstname'
        video.user.last_name = 'lastname'
        video.user.save()
        video.save()

        video2 = Video.objects.get(pk=47)
        video2.user = video.user
        video2.authors = [video.user]
        video2.save()

        self._rebuild_index()

        excluded = self.search('-user:superuser')
        for e in excluded:
            # should not include the superuser videos
            self.assertNotEquals(e, video)
            self.assertNotEquals(e, video2)

    def test_search_includes_service_user(self):
        """
        Search should search the video service user for videos.
        """
        video = Video.objects.get(pk=20)
        video.video_service_user = 'Video_service_user'
        video.save()

        self._rebuild_index()
        self.assertEqual(self.search('video_service_user'), [video])

    def test_search_includes_feed_name(self):
        """
        Search should search the feed name for videos.
        """
        feed = Feed.objects.get(name='miropcf')

        self._rebuild_index()

        videos = self.search('miropcf')
        for video in videos:
            self.assertEqual(video.feed_id, feed.pk)

        videos = self.search('feed:miropcf')
        for video in videos:
            self.assertEqual(video.feed_id, feed.pk)

        videos = self.search('feed:%i' % feed.pk)
        for video in videos:
            self.assertEqual(video.feed_id, feed.pk)

    def test_search_exclude_terms(self):
        """
        Search should exclude terms that start with - (hyphen).
        """
        self._rebuild_index()
        results = search.auto_query('-blender')
        self.assertTrue(results)
        for result in results:
            self.assertFalse('blender' in result.text.lower())

    def test_search_unicode(self):
        """
        Search should handle Unicode strings.
        """
        self._rebuild_index()
        self.assertEqual(self.search(u'espa\xf1a'), [])

    def test_search_includes_playlist(self):
        """
        Search should include the playlists a video is a part of.
        """
        user = User.objects.get(username='user')
        playlist = Playlist.objects.create(
            user=user,
            name='Test List',
            slug='test-list',
            description="This is a list for testing")
        video = Video.objects.get(pk=20)
        playlist.add_video(video)

        self._rebuild_index()

        self.assertEqual(self.search('playlist:%i' % playlist.pk), [video])
        self.assertEqual(self.search('playlist:user/test-list'), [video])

    def test_search_includes_search(self):
        """
        Search should include the saved search a video came from.
        """
        video = Video.objects.get(pk=20)
        search = SavedSearch.objects.get(pk=6) # Participatory Culture
        video.search = search
        video.save()

        self._rebuild_index()

        self.assertEqual(self.search('search:%i' % search.pk), [video])
        self.assertEqual(self.search('search:"Participatory Culture"'),
                          [video])

    def test_search_or(self):
        """
        Terms bracketed in {}s should be ORed together.
        """
        self._rebuild_index()
        results = search.auto_query('{elephant render}')
        self.assertTrue(results)
        for result in results:
            self.assertTrue(('elephant' in result.text.lower()) or
                            ('render' in result.text.lower()), result.text)

    def test_search_or_and(self):
        """
        Mixing OR and AND should work as expected.
        """
        self._rebuild_index()
        results = search.auto_query('{import repair} -and')
        self.assertTrue(results)
        for result in results:
            self.assertFalse('and' in result.text.lower(), result.text)
            self.assertTrue(('import' in result.text.lower()) or
                            ('repair' in result.text.lower()), result.text)
