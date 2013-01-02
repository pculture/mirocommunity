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

    def test_POST(self):
        """
        Submitting a POST request to the add URL should create the feed for
        real, import the feed, and redirect back to the admin page.
        """
        feed_url = 'http://google.com/'
        self.assertRaises(Feed.DoesNotExist, Feed.objects.get)
        response = self.client.post(self.url, {'feed_url': feed_url})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'],
                          'http://testserver%s' % (reverse('localtv_admin_manage_page')))
        feed = Feed.objects.get()
        finish_by = time.time() + 5 # 5s timeout
        while feed.status == feed.INACTIVE and time.time() < finish_by:
            time.sleep(0.3)
            feed = Feed.objects.get()

        self.assertEqual(feed.feed_url, feed_url)
        self.assertEqual(feed.status, Feed.ACTIVE)
        self.assertEqual(feed.name, u'Yahoo Media TEST')
        self.assertEqual(feed.description, u'This is a PCF-governed RSS 2.0 feed to '
                                           u'test Yahoo media enclosures. All '
                                           u'contents of this feed are for example only.')
        self.assertEqual(feed.webpage, u'http://qa.pculture.org/feeds_test/feed1')
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
        response = self.client.post(self.url,
                                    {'feed_url': 'http://google.com/',
                                     'auto_approve': 'yes'})
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
