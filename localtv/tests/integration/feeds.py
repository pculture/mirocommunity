# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
#
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community. If not, see <http://www.gnu.org/licenses/>.

from django.contrib.auth.models import User
from django.test.client import Client

import datetime
import json

from localtv.models import Video
from localtv.playlists.models import Playlist
from localtv.tests.base import BaseTestCase


class FeedViewIntegrationTestCase(BaseTestCase):
    urls = 'localtv.urls'

    def setUp(self):
        BaseTestCase.setUp(self)
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
        self.assertEqual(1, len(data['items']))
        self.assertEqual(data['items'][0]['title'], bar_video.name)

        response = client.get('/feeds/json/search/foo') # best match
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], u'example.com: Search: foo')
        self.assertEqual(2, len(data['items']))
        self.assertEqual(data['items'][0]['title'], self.yesterday_video.name)

        response = client.get('/feeds/json/search/foo', {'sort': 'latest'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], u'example.com: Search: foo')
        self.assertEqual(2, len(data['items']))
        self.assertEqual(data['items'][0]['title'], bar_video.name)

    def test_playlist_feed(self):
        user = User.objects.create(username='user')
        playlist = Playlist.objects.create(name='Test Playlist',
                                           slug='test-playlist',
                                           user=user)
        playlist.add_video(self.test_video)
        playlist.add_video(self.yesterday_video)

        client = Client()
        response = client.get('/feeds/json/playlist/1')
        self.assertEqual(response.status_code, 200, response)
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'example.com: Playlist: Test Playlist')
        self.assertEqual(2, len(data['items']))
        # first in the order, first in the feed
        self.assertEqual(data['items'][0]['title'], self.test_video.name)

        response = client.get('/feeds/json/playlist/1?sort=order')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'example.com: Playlist: Test Playlist')
        self.assertEqual(2, len(data['items']))
        # yesterday video last in the order, should appear first
        self.assertEqual(data['items'][0]['title'], self.yesterday_video.name)

