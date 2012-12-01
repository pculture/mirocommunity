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

import time

from django.core.urlresolvers import reverse
import feedparser
from mock import patch
from vidscraper import VideoFeed

from localtv import tasks
from localtv.models import Video, Feed
from localtv.tests import BaseTestCase


class AdminFeedImportIntegrationTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.url = reverse('localtv_admin_feed_add')
        with self._data_file('feeds/qa1.rss') as f:
            feed = feedparser.parse(f.read())
        patcher = patch.object(VideoFeed, 'get_url_response', lambda *args, **kwargs: feed)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(tasks, 'video_save_thumbnail')
        self.save_thumbnail = patcher.start()
        self.addCleanup(patcher.stop)
        self.create_user(username='admin', password='admin', is_superuser=True)
        self.client.login(username='admin', password='admin')

    def test_GET(self):
        """
        A GET request to the add_feed() view should include a form to set the
        auto_approve, category, and user fields on the newly created feed.  The
        form should also have an instance of a Feed object with some
        information about the feed.  There should be a `video_count` variable
        in the context which has the number of videos in the feed.
        """
        response = self.client.get(self.url, {'feed_url': 'http://google.com/'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['video_count'], 6)
        form = response.context['form']
        instance = form.instance
        self.assertEqual(instance.id, None) # not created yet
        self.assertEqual(instance.feed_url, 'http://google.com/')
        self.assertEqual(instance.status, instance.INACTIVE)
        self.assertEqual(instance.name, 'Yahoo Media TEST')
        self.assertEqual(instance.description,
                         """This is a PCF-governed RSS 2.0 feed to test Yahoo \
media enclosures. All contents of this feed are for example only.""")

        self.assertFalse(form.is_bound)

    def test_GET_invalid_url(self):
        """
        If the URL isn't valid, the view should return a 400 code with some
        description about the error.
        """
        response = self.client.get(self.url, {'feed_url':
                                                  'foo://example.invalid/'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, '* Enter a valid URL.')

    def test_POST(self):
        """
        Submitting a POST request to the add URL should create the feed for
        real, import the feed, and redirect back to the admin page.
        """
        response = self.client.post('%s?feed_url=%s' % (self.url,
                                                        'http://google.com/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'],
                          'http://testserver%s' % (reverse('localtv_admin_manage_page')))
        feed = Feed.objects.get()
        finish_by = time.time() + 5 # 5s timeout
        while feed.status == feed.INACTIVE and time.time() < finish_by:
            time.sleep(0.3)
            feed = Feed.objects.get()

        self.assertEqual(feed.status, Feed.ACTIVE)
        feed_import = feed.imports.get()
        self.assertEqual(feed_import.status, feed_import.COMPLETE)
        self.assertEqual(feed_import.total_videos, 6)
        self.assertEqual(feed_import.videos_imported, 2)
        self.assertEqual(feed_import.videos_skipped, 4)
        self.assertEqual(self.save_thumbnail.delay.call_count, 2)

        self.assertEqual(
            feed.video_set.filter(status=Video.UNAPPROVED).count(), 2)

    def test_POST_auto_approve(self):
        """
        Submitting a POST request with 'auto_approve' set to True should
        approve all the videos.
        """
        response = self.client.post('%s?feed_url=%s' % (self.url,
                                                        'http://google.com/'),
                                    {'auto_approve': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'],
                         'http://testserver%s' % (reverse('localtv_admin_manage_page')))
        feed = Feed.objects.get()
        finish_by = time.time() + 5 # 5s timeout
        while feed.status == feed.INACTIVE and time.time() < finish_by:
            time.sleep(0.3)
            feed = Feed.objects.get()
        self.assertEqual(feed.status, Feed.ACTIVE)
        self.assertEqual(feed.auto_approve, True)
        feed_import = feed.imports.get()
        self.assertEqual(feed_import.auto_approve, True)
        self.assertEqual(feed_import.status, feed_import.COMPLETE)
        self.assertEqual(feed_import.total_videos, 6)
        self.assertEqual(feed_import.videos_imported, 2)
        self.assertEqual(feed_import.videos_skipped, 4)
        self.assertEqual(self.save_thumbnail.delay.call_count, 2)

        self.assertEqual(
            feed.video_set.filter(status=Video.ACTIVE).count(), 2)
