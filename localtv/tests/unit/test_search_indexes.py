from haystack import connections
from haystack.query import SearchQuerySet

from localtv.models import Video
from localtv.tests import BaseTestCase


class VideoIndexUnitTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.index = connections['default'].get_unified_index().get_index(
                                                                        Video)

    def _test_delete_cascade(self, related_object, field_name):
        self._clear_index()
        video = self.create_video(**{"%s_id" % field_name: related_object.pk})

        expected = set((video.pk,))
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)

        related_object.delete()
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, set())

    def test_delete_cascade__feed(self):
        """
        Deletion of feeds, searches, sites, and users should also remove their
        related videos from the index.

        """
        self._test_delete_cascade(self.create_feed('http://google.com'),
                                  'feed')

    def test_delete_cascade__search(self):
        """
        Deletion of feeds, searches, sites, and users should also remove their
        related videos from the index.

        """
        self._test_delete_cascade(self.create_search('search'), 'search')

    def test_delete_cascade__user(self):
        """
        Deletion of feeds, searches, sites, and users should also remove their
        related videos from the index.

        """
        self._test_delete_cascade(self.create_user(username='test'), 'user')

    def test_delete_cascade__site(self):
        """
        Deletion of feeds, searches, sites, and users should also remove their
        related videos from the index.

        """
        self._test_delete_cascade(self.create_site(), 'site')

    def test_related_update__playlistitem(self):
        """
        Adding a video to a playlist and removing it from the playlist should
        each update the index.

        """
        self._clear_index()
        video = self.create_video()
        # For completeness, check beforehand.
        r = SearchQuerySet()[0]
        self.assertEqual(r.playlists, [])

        user = self.create_user(username='user')
        playlist = self.create_playlist(user)
        playlist.add_video(video)
        r = SearchQuerySet()[0]
        self.assertEqual([int(pk) for pk in r.playlists], [playlist.pk])

        playlist.playlistitem_set.get().delete()
        r = SearchQuerySet()[0]
        self.assertEqual(r.playlists, [])
