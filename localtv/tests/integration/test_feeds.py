from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test.client import Client

import datetime
import json
import feedparser

from localtv.models import Video, Feed, SiteSettings
from localtv.admin import feeds
from localtv.playlists.models import Playlist
from localtv.tests import BaseTestCase


class FeedViewIntegrationTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        SiteSettings.objects.create(site_id=1)
        self._clear_index()
        now = datetime.datetime.now()
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        self.test_video = self.create_video(
            when_submitted=now,
            when_approved=now,
            when_published=now)
        self.yesterday_video = self.create_video(
            name='Foo Foo',
            when_submitted=yesterday,
            when_approved=yesterday,
            when_published=yesterday)
        self.unapproved_video = self.create_video(status=Video.UNAPPROVED)

    def test_search_feed(self):
        bar_video = self.create_video(name='Foo Bar')

        client = Client()
        response = client.get('/feeds/json/search/foo bar')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], u'example.com: Search: foo bar')
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['title'], bar_video.name)

        # Default sort should be best match.
        response = client.get('/feeds/json/search/foo')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], u'example.com: Search: foo')
        self.assertEqual(len(data['items']), 2)
        self.assertEqual(data['items'][0]['title'], self.yesterday_video.name)

        response = client.get('/feeds/json/search/foo', {'sort': 'newest'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], u'example.com: Search: foo')
        self.assertEqual(len(data['items']), 2)
        self.assertEqual(data['items'][0]['title'], bar_video.name)

        # Backwards-compatibility check.
        response = client.get('/feeds/json/search/foo', {'sort': 'latest'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], u'example.com: Search: foo')
        self.assertEqual(len(data['items']), 2)
        self.assertEqual(data['items'][0]['title'], bar_video.name)

    def test_playlist_feed(self):
        user = User.objects.create(username='user')
        playlist = Playlist.objects.create(name='Test Playlist',
                                           slug='test-playlist',
                                           user=user,
                                           site=Site.objects.get_current())
        playlist.add_video(self.test_video)
        playlist.add_video(self.yesterday_video)
        self._rebuild_index()

        client = Client()
        response = client.get('/feeds/json/playlist/1')
        self.assertEqual(response.status_code, 200, response)
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'example.com: Playlist: Test Playlist')
        self.assertEqual(len(data['items']), 2)
        # first in the order, first in the feed
        self.assertEqual(data['items'][0]['title'], self.test_video.name)

        client = Client()
        response = client.get('/feeds/json/playlist/1?sort=order')
        self.assertEqual(response.status_code, 200, response)
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'example.com: Playlist: Test Playlist')
        self.assertEqual(len(data['items']), 2)
        # first in the order, first in the feed
        self.assertEqual(data['items'][0]['title'], self.test_video.name)

        response = client.get('/feeds/json/playlist/1?sort=-order')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'example.com: Playlist: Test Playlist')
        self.assertEqual(len(data['items']), 2)
        # yesterday video last in the order, should appear first
        self.assertEqual(data['items'][0]['title'], self.yesterday_video.name)

        response = client.get('/feeds/json/playlist/2')
        self.assertEqual(response.status_code, 404)


class AdminFeedViewIntegrationTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        SiteSettings.objects.create(site_id=1)
        self.feed = Feed.objects.create(name='Feed', site_id=1,
                                        last_updated=datetime.datetime.now())
        self.unapproved_video = self.create_video('Feed Video',
                                                  status=Video.UNAPPROVED,
                                                  feed=self.feed)
        self.unapproved_user_video = self.create_video('User Video',
                                                       status=Video.UNAPPROVED)

    def test_unapproved(self):
        url = reverse('localtv_admin_feed_unapproved',
                      args=[feeds.generate_secret()])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        fp = feedparser.parse(response.content)
        expected_titles = Video.objects.filter(
            status=Video.UNAPPROVED,
            site=1).order_by('when_submitted', 'when_published'
            ).values_list('name', flat=True)
        self.assertEquals([entry.title for entry in fp.entries],
                          list(expected_titles))

    def test_unapproved_user(self):
        url = reverse('localtv_admin_feed_unapproved_user',
                      args=[feeds.generate_secret()])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        fp = feedparser.parse(response.content)
        expected_titles = Video.objects.filter(
            status=Video.UNAPPROVED, feed=None, search=None,
            site=1).order_by('when_submitted', 'when_published'
            ).values_list('name', flat=True)
        self.assertEquals([entry.title for entry in fp.entries],
                          list(expected_titles))
