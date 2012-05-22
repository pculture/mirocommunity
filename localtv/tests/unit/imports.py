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

import datetime

from celery.signals import task_postrun
from haystack.query import SearchQuerySet
from vidscraper.suites import Video as VidscraperVideo

from localtv.models import Source, Feed, FeedImport, Video
from localtv.tasks import haystack_update, haystack_remove
from localtv.tests.base import BaseTestCase


class FeedImportUnitTestCase(BaseTestCase):

    def create_vidscraper_video(self, url='http://youtube.com/watch/?v=fake',
                                loaded=True, embed_code='hi', title='Test',
                                **field_data):
        video = VidscraperVideo(url)
        video._loaded = loaded
        field_data.update({'embed_code': embed_code, 'title': title})
        for key, value in field_data.items():
            setattr(video, key, value)

        return video

    def test_update_approved_feed(self):
        feed = self.create_feed('http://google.com', status=Feed.INACTIVE)
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video(),
            self.create_vidscraper_video()
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        self.assertEqual(Feed.objects.get(pk=feed.pk).status, Feed.ACTIVE)

    def test_auto_approve_True(self):
        """
        If Feed.auto_approve is True, the imported videos should be marked as
        active.
        """
        feed = self.create_feed('http://google.com', auto_approve=True)
        feed_import = FeedImport.objects.create(source=feed,
                                                auto_approve=True)
        video_iter = [
            self.create_vidscraper_video(),
            self.create_vidscraper_video()
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        self.assertEqual(Video.objects.count(), 2)
        self.assertEqual(Video.objects.filter(
                status=Video.ACTIVE).count(), 2)

    def test_auto_approve_False(self):
        """
        If Feed.auto_approve is False, the imported videos should be marked as
        unapproved.
        """
        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video(),
            self.create_vidscraper_video()
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        self.assertEqual(Video.objects.count(), 2)
        self.assertEqual(Video.objects.filter(
                status=Video.UNAPPROVED).count(), 2)

    def test_entries_inserted_in_feed_order(self):
        """
        When adding entries from a feed, they should be sortable so that the
        first item in the feed is the first item returned.
        """
        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video(guid='2'),
            self.create_vidscraper_video(guid='1')
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        db_guids = Video.objects.in_feed_order().values_list('guid',
                                                             flat=True)
        self.assertEqual(list(db_guids), ['1', '2'])

    def test_ignore_duplicate_guid(self):
        """
        If an item with a certain GUID is in a feed twice, but not in the
        database at all, it should only be imported once.
        """
        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video(guid='duplicate'),
            self.create_vidscraper_video(guid='duplicate')
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        feed_import = FeedImport.objects.get(pk=feed_import.pk) # reload
        self.assertEqual(feed_import.videos_skipped, 1)
        self.assertEqual(feed_import.videos_imported, 1)
        self.assertEqual(Video.objects.count(), 1)

    def test_ignore_duplicate_link(self):
        """
        If an item with a certain link is in a feed twice, but not in the
        database at all, it should only be imported once.
        """
        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video(link='http://duplicate.com/'),
            self.create_vidscraper_video(link='http://duplicate.com/')
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        feed_import = FeedImport.objects.get(pk=feed_import.pk) # reload
        self.assertEqual(feed_import.videos_skipped, 1)
        self.assertEqual(feed_import.videos_imported, 1)
        self.assertEqual(Video.objects.count(), 1)

    def test_entries_include_feed_data(self):
        """
        Videos imported from feeds should pull the following from the RSS feed:
        * GUID
        * name
        * description (sanitized)
        * website URL
        * publish date
        * file URL
        * file length
        * file MIME type
        * thumbnail
        * tags
        """
        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video(
                guid='guid',
                title='title',
                description='description',
                link='http://example.com/link',
                file_url='http://example.com/file_url',
                file_url_length=1000,
                file_url_mimetype='video/mimetype',
                # MySQL doesn't store the microseconds (and we don't much care
                # about them), so don't bother inserting them.  This makes the
                # assertion below about the published date equality True.
                publish_datetime=datetime.datetime.now().replace(
                    microsecond=0),
                tags=['tag1', 'tag2']
                ),
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        vv = video_iter[0]
        video = Video.objects.get()
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.guid, vv.guid)
        self.assertEqual(video.name, vv.title)
        self.assertEqual(video.description, vv.description)
        self.assertEqual(video.website_url, vv.link)
        self.assertEqual(video.embed_code, vv.embed_code)
        self.assertEqual(video.file_url, vv.file_url)
        self.assertEqual(video.file_url_length, vv.file_url_length)
        self.assertEqual(video.file_url_mimetype, vv.file_url_mimetype)
        self.assertEqual(video.when_published, vv.publish_datetime)
        self.assertEqual([tag.name for tag in video.tags.all()], vv.tags)

    def test_entries_link_optional(self):
        """
        A link in the feed to the original source should be optional.
        """
        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video()
            ]
        video_iter[0].url = video_iter[0].link = None
        Source.update(feed, video_iter, feed_import, using='default')
        self.assertEqual(Video.objects.count(), 1)

    def test_entries_enclosure_type_optional(self):
        """
        An enclosure without a MIME type, but with a file URL extension we
        think is media, should be imported.
        """
        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video(
                file_url='http://example.com/media.ogg')
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        self.assertEqual(Video.objects.count(), 1)

    def test_entries_multiple_imports(self):
        """
        Importing a feed multiple times shouldn't overwrite the existing
        videos.
        """
        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video(guid='2'),
            self.create_vidscraper_video(guid='1')
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        feed_import = FeedImport.objects.get(pk=feed_import.pk) # reload
        self.assertEqual(feed_import.videos_skipped, 0)
        self.assertEqual(feed_import.videos_imported, 2)
        self.assertEqual(Video.objects.count(), 2)

        feed_import2 = FeedImport.objects.create(source=feed)
        Source.update(feed, video_iter, feed_import2, using='default')
        feed_import2 = FeedImport.objects.get(pk=feed_import2.pk) # reload
        self.assertEqual(feed_import2.videos_skipped, 2)
        self.assertEqual(feed_import2.videos_imported, 0)
        self.assertEqual(Video.objects.count(), 2)

    def test_entries_from_mc(self):
        """
        Atom feeds generated by Miro Community should be handled as if the item
        was imported from the original feed.
        """
        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video(
                url='http://testserver/video/1234/title',
                link='http://example.com/link',
                description="""
<div class="miro-community-description">Original Description</div>
<p>
Original Link: <a href="http://example.com/link">http://example.com/link</a>
</p>""",

                ),
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        vv = video_iter[0]
        video = Video.objects.get()
        self.assertEqual(video.website_url, vv.link)
        self.assertEqual(video.description, "Original Description")


    def test_entries_atom_with_long_item(self):
        """
        Feeds with long file URLs (>200 characters) should be loaded into the
        database normally.
        """
        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed)
        video_iter = [
            self.create_vidscraper_video(
                url='http://example.com/' + 'url' * 200,
                link='http://example.com/' + 'link' * 200,
                file_url='http://example.com/' + 'f.ogg' * 200)
            ]
        Source.update(feed, video_iter, feed_import, using='default')
        v = Video.objects.get()
        self.assertEqual(v.website_url, video_iter[0].link)
        self.assertEqual(v.file_url, video_iter[0].file_url)

    def test_index_updates(self):
        """Test that index updates are only run at the end of an update."""
        self.updates = 0
        self.removals = 0

        def count_update(sender, **kwargs):
            self.updates += 1
        task_postrun.connect(count_update, sender=haystack_update)

        def count_removal(sender, **kwargs):
            self.removals += 1
        task_postrun.connect(count_removal, sender=haystack_remove)

        feed = self.create_feed('http://google.com')
        feed_import = FeedImport.objects.create(source=feed,
                                                auto_approve=True)
        video_iter = [
            self.create_vidscraper_video(),
            self.create_vidscraper_video(),
            self.create_vidscraper_video(),
        ]
        Source.update(feed, video_iter, feed_import, using='default')
        self.assertEqual(self.updates, 1)
        self.assertEqual(self.removals, 0)
        self.assertEqual(SearchQuerySet().count(), len(video_iter))
