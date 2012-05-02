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

from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from localtv.tests.legacy_localtv import BaseTestCase

from localtv.search.query import SmartSearchQuerySet
from localtv.models import Video, SavedSearch, Feed
from localtv.playlists.models import Playlist

class LegacyAutoQueryTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['categories', 'feeds', 'savedsearches',
                                        'videos']

    def search(self, query):
        return [result.object for result in SmartSearchQuerySet().auto_query(query)]

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

        excluded = self.search('-user:superuser')
        for e in excluded:
            # should not include the superuser videos
            self.assertNotEquals(e, video)
            self.assertNotEquals(e, video2)

    def test_search_exclude_terms(self):
        """
        Search should exclude terms that start with - (hyphen).
        """
        results = SmartSearchQuerySet().auto_query('-blender')
        self.assertTrue(results)
        for result in results:
            self.assertFalse('blender' in result.text.lower())

    def test_search_includes_playlist(self):
        """
        Search should include the playlists a video is a part of.
        """
        user = User.objects.get(username='user')
        playlist = Playlist.objects.create(
            site=Site.objects.get_current(),
            user=user,
            name='Test List',
            slug='test-list',
            description="This is a list for testing")
        video = Video.objects.get(pk=20)
        playlist.add_video(video)

        self.assertEqual(self.search('playlist:%i' % playlist.pk), [video])
        self.assertEqual(self.search('playlist:user/test-list'), [video])

        playlist.playlistitem_set.all().delete()

        self.assertEqual(self.search('playlist:%i' % playlist.pk), [])
        self.assertEqual(self.search('playlist:user/test-list'), [])

    def test_search_includes_search(self):
        """
        Search should include the saved search a video came from.
        """
        video = Video.objects.get(pk=20)
        search = SavedSearch.objects.get(pk=6) # Participatory Culture
        video.search = search
        video.save()

        self.assertEqual(self.search('search:%i' % search.pk), [video])
        self.assertEqual(self.search('search:"Participatory Culture"'),
                          [video])

    def test_search_or(self):
        """
        Terms bracketed in {}s should be ORed together.
        """
        results = SmartSearchQuerySet().auto_query('{elephant render}')
        self.assertGreater(len(results), 0)
        for result in results:
            self.assertTrue(('elephant' in result.text.lower()) or
                            ('render' in result.text.lower()), result.text)

    def test_search_or__user_first(self):
        """
        bz19056. If the first term in {} is a user: keyword search, it should
        behave as expected.
        """
        user = User.objects.get(username='admin')
        results = SmartSearchQuerySet().auto_query('{user:admin repair}')
        self.assertGreater(len(results), 0)
        for result in results:
            self.assertTrue('repair' in result.text.lower() or
                            unicode(result.user) == unicode(user.pk) or
                            unicode(user.pk) in [unicode(a)
                                                 for a in result.authors])

    def test_search_or_and(self):
        """
        Mixing OR and AND should work as expected.
        """
        # this used to be '{import repair} -and' but that no longer works.  I
        # wonder if recent versions of Haystack (or Whoosh) skip small words?
        results = SmartSearchQuerySet().auto_query(
            '{import repair} -positioning')
        self.assertGreater(len(results), 0)
        for result in results:
            self.assertFalse('positioning' in result.text.lower(), result.text)
            self.assertTrue(('import' in result.text.lower()) or
                            ('repair' in result.text.lower()), result.text)
