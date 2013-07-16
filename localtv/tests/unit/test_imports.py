import datetime

from celery.signals import task_postrun
from haystack.query import SearchQuerySet
import mock
import vidscraper
from vidscraper.suites.youtube import Suite as YouTubeSuite
from vidscraper.videos import (Video as VidscraperVideo,
                               VideoFile as VidscraperVideoFile)

from localtv.models import Source, Feed, FeedImport, Video, FeedImportIndex
from localtv.tasks import haystack_update, haystack_remove, video_save_thumbnail
from localtv.tests import BaseTestCase


class SourceImportUnitTestCase(BaseTestCase):
    def test_iter_exception(self):
        """
        bz19448. If an exception is raised while iterating over vidscraper
        results, the import should be marked as failed, and any videos already
        associated with the import should be deleted.

        """
        def iterator():
            raise KeyError
            yield 1
        video_iter = iterator()
        with self.assertRaises(KeyError):
            video_iter.next()
        video_iter = iterator()
        feed = self.create_feed('http://google.com/')
        video = self.create_video(feed=feed, status=Video.PENDING,
                                  update_index=False)
        feed_import = FeedImport.objects.create(auto_approve=True,
                                                source=feed)
        FeedImportIndex.objects.create(source_import=feed_import,
                                       video=video)
        self.assertEqual(list(feed_import.get_videos()), [video])
        self.assertEqual(list(feed.video_set.all()), [video])
        self.assertEqual(feed_import.errors.count(), 0)
        # If this is working correctly, this next line should not raise
        # a KeyError.
        Source.update(feed, video_iter, feed_import)
        new_feed_import = FeedImport.objects.get(pk=feed_import.pk)
        self.assertEqual(new_feed_import.status, FeedImport.FAILED)
        with self.assertRaises(Video.DoesNotExist):
            Video.objects.get(pk=video.pk)
        self.assertEqual(feed_import.errors.count(), 1)


class FeedImportUnitTestCase(BaseTestCase):
    def create_vidscraper_video(self, url='http://youtube.com/watch/?v=fake',
                                loaded=True, embed_code='hi', title='Test',
                                **field_data):
        video = vidscraper.videos.Video(url)
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
        Source.update(feed, video_iter, feed_import)
        self.assertEqual(Feed.objects.get(pk=feed.pk).status, Feed.PUBLISHED)

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
        Source.update(feed, video_iter, feed_import)
        self.assertEqual(Video.objects.count(), 2)
        self.assertEqual(Video.objects.filter(
                status=Video.PUBLISHED).count(), 2)

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
        Source.update(feed, video_iter, feed_import)
        self.assertEqual(Video.objects.count(), 2)
        self.assertEqual(Video.objects.filter(
                status=Video.NEEDS_MODERATION).count(), 2)

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
        Source.update(feed, video_iter, feed_import)
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
        Source.update(feed, video_iter, feed_import)
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
        Source.update(feed, video_iter, feed_import)
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
                files=[VidscraperVideoFile('http://example.com/file_url',
                                           length=1000,
                                           mime_type='video/mimetype')],
                # MySQL doesn't store the microseconds (and we don't much care
                # about them), so don't bother inserting them.  This makes the
                # assertion below about the published date equality True.
                publish_datetime=datetime.datetime.now().replace(
                    microsecond=0),
                tags=['tag1', 'tag2']
                ),
            ]
        Source.update(feed, video_iter, feed_import)
        vv = video_iter[0]
        video = Video.objects.get()
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.guid, vv.guid)
        self.assertEqual(video.name, vv.title)
        self.assertEqual(video.description, vv.description)
        self.assertEqual(video.website_url, vv.link)
        self.assertEqual(video.embed_code, vv.embed_code)
        self.assertEqual(video.file_url, vv.files[0].url)
        self.assertEqual(video.file_url_length, vv.files[0].length)
        self.assertEqual(video.file_url_mimetype, vv.files[0].mime_type)
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
        Source.update(feed, video_iter, feed_import)
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
                files=[VidscraperVideoFile('http://example.com/media.ogg')])
            ]
        Source.update(feed, video_iter, feed_import)
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
        Source.update(feed, video_iter, feed_import)
        feed_import = FeedImport.objects.get(pk=feed_import.pk) # reload
        self.assertEqual(feed_import.videos_skipped, 0)
        self.assertEqual(feed_import.videos_imported, 2)
        self.assertEqual(Video.objects.count(), 2)

        feed_import2 = FeedImport.objects.create(source=feed)
        Source.update(feed, video_iter, feed_import2)
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
        Source.update(feed, video_iter, feed_import)
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
                files=[VidscraperVideoFile('http://example.com/' + 'f.ogg' * 200)])
            ]
        Source.update(feed, video_iter, feed_import)
        v = Video.objects.get()
        self.assertEqual(v.website_url, video_iter[0].link)
        self.assertEqual(v.file_url, video_iter[0].files[0].url)

    def test_index_updates(self):
        """Test that index updates are only run at the end of an update."""
        self.updates = 0
        self.removals = 0
        self._clear_index()

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
        Source.update(feed, video_iter, feed_import)
        self.assertEqual(self.updates, 1)
        self.assertEqual(self.removals, 0)
        self.assertEqual(SearchQuerySet().count(), len(video_iter))


class SavedSearch(BaseTestCase):
    def _search(self, query, *args, **kwargs):
        search = YouTubeSuite.search_class(query)
        response = self.get_response(self._vidscraper_data_file('youtube/search.json'))
        with mock.patch.object(search, 'get_page', return_value=response):
            search._next_page()
        return [search]

    @staticmethod
    def _load(video):
        video.embed_code = 'haha!'

    def test_update(self):
        """
        SavedSearch.update() should create new Video objects linked to
        the search. Updating a second time shouldn't re-add videos.
        """
        search = self.create_search('blah rocket')
        self.assertEqual(search.video_set.count(), 0)
        with mock.patch.object(VidscraperVideo, 'load', self._load):
            with mock.patch.object(vidscraper, 'auto_search', self._search):
                with mock.patch.object(video_save_thumbnail, 'delay'):
                    search.update()
        self.assertEqual(search.video_set.count(), 5)
        with mock.patch.object(VidscraperVideo, 'load', self._load):
            with mock.patch.object(vidscraper, 'auto_search', self._search):
                with mock.patch.object(video_save_thumbnail, 'delay'):
                    search.update()
        self.assertEqual(search.video_set.count(), 5)

    def test_update_auto_authors(self):
        """
        If a SavedSearch has authors set, imported videos should be given that
        authorship.
        """
        search = self.create_search('blah rocket')
        user = self.create_user()
        search.auto_authors = [user]
        with mock.patch.object(VidscraperVideo, 'load', self._load):
            with mock.patch.object(vidscraper, 'auto_search', self._search):
                with mock.patch.object(video_save_thumbnail, 'delay'):
                    search.update()
        self.assertTrue(user in list(search.video_set.all()[0].authors.all()))

    def test_attribution_default(self):
        """
        If a SavedSearch has no author, imported videos should have a User
        based on the user on the original video service.
        """
        search = self.create_search('blah rocket')
        self.assertFalse(search.auto_authors.all().exists())
        with mock.patch.object(VidscraperVideo, 'load', self._load):
            with mock.patch.object(vidscraper, 'auto_search', self._search):
                with mock.patch.object(video_save_thumbnail, 'delay'):
                    search.update()
        self.assertTrue(search.video_set.all()[0].authors.all().exists())
