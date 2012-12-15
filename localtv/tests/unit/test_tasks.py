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

from datetime import datetime, timedelta

from celery.signals import task_postrun
from django.db import connections
from django.test.utils import override_settings
from haystack.query import SearchQuerySet
import mock

from localtv.models import Video
from localtv.tasks import (haystack_update, haystack_remove,
                           haystack_batch_update, video_from_vidscraper_video,
                           video_save_thumbnail)
from localtv.tests import BaseTestCase


class VideoFromVidscraperTestCase(BaseTestCase):
    def test_m2m_errors(self):
        """
        If video.save_m2m raises an exception during import, the video should
        be deleted and the error reraised.

        """
        class FakeException(Exception):
            pass
        video = mock.MagicMock(save_m2m=mock.MagicMock(
                                                   side_effect=FakeException))
        kwargs = {'from_vidscraper_video.return_value': video}
        vidscraper_video = mock.MagicMock(link=None, guid=None, user=None)

        with mock.patch('localtv.tasks.get_model'):
            with mock.patch('localtv.tasks.Video', **kwargs):
                with self.assertRaises(FakeException):
                    video_from_vidscraper_video.apply(args=(vidscraper_video, 1))

        video.save.assert_called_once_with(update_index=False)
        video.save_m2m.assert_called_once_with()
        video.delete.assert_called_once_with()


class HaystackUpdateUnitTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self._clear_index()
        self.video0 = self.create_video(name='Unapproved',
                                        status=Video.UNAPPROVED,
                                        update_index=False)
        self.video1 = self.create_video(name='Video1', update_index=False)
        self.video2 = self.create_video(name='Video2', update_index=False)
        self.video3 = self.create_video(name='Video3', update_index=False)
        self.video4 = self.create_video(name='Video4', update_index=False)

    def test(self):
        expected = set()
        results = set((r.pk for r in SearchQuerySet()))
        self.assertEqual(results, expected)

        all_pks = [self.video0.pk, self.video1.pk, self.video2.pk,
                   self.video3.pk, self.video4.pk]
        haystack_update.apply(args=(Video._meta.app_label,
                                    Video._meta.module_name,
                                    all_pks))
        expected = set(all_pks[1:])
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)

    def test_remove(self):
        """
        Any instances which are not in the main queryset should be removed if
        the ``remove`` kwarg is ``True``.

        """
        all_pks = [self.video0.pk, self.video1.pk, self.video2.pk,
                   self.video3.pk, self.video4.pk]
        haystack_update.apply(args=(Video._meta.app_label,
                                    Video._meta.module_name,
                                    all_pks))

        # If remove is True, the changed instance should be removed.
        self.video1.status = Video.REJECTED
        self.video1.save(update_index=False)
        expected = set(all_pks[1:])
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)

        haystack_update.apply(args=(Video._meta.app_label,
                                    Video._meta.module_name,
                                    all_pks),
                              kwargs={'remove': True})
        expected = set(all_pks[2:])
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)

        # Otherwise, it shouldn't be removed.
        self.video2.status = Video.REJECTED
        self.video2.save(update_index=False)
        expected = set(all_pks[2:])
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)

        haystack_update.apply(args=(Video._meta.app_label,
                                    Video._meta.module_name,
                                    all_pks),
                              kwargs={'remove': False})
        expected = set(all_pks[2:])
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)


class HaystackRemoveUnitTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self._clear_index()
        self.video1 = self.create_video(name='Video1')
        self.video2 = self.create_video(name='Video2')
        self.video3 = self.create_video(name='Video3')
        self.video4 = self.create_video(name='Video4')

    def test(self):
        all_pks = [self.video1.pk, self.video2.pk,
                   self.video3.pk, self.video4.pk]

        expected = set(all_pks)
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)

        haystack_remove.apply(args=(Video._meta.app_label,
                                    Video._meta.module_name,
                                    all_pks[2:]))

        expected = set(all_pks[:2])
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)


class HaystackBatchUpdateUnitTestCase(BaseTestCase):
    def test_batch(self):
        """Tests whether batching works."""
        self._clear_index()
        video1 = self.create_video(name='Video1', update_index=False)
        video2 = self.create_video(name='Video2', update_index=False)
        video3 = self.create_video(name='Video3', update_index=False)
        expected = set()
        results = set((r.pk for r in SearchQuerySet()))
        self.assertEqual(results, expected)

        self.batches = 0
        def count_batch(sender, **kwargs):
            self.batches = self.batches + 1
        task_postrun.connect(count_batch, sender=haystack_update)

        haystack_batch_update.apply(args=(Video._meta.app_label,
                                          Video._meta.module_name),
                                    kwargs={'batch_size': 1})
        self.assertEqual(self.batches, 3)

        expected = set((video1.pk, video2.pk, video3.pk))
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)

    def test_date_filtering(self):
        """
        It should be possible to filter the batch update by a start and
        end date for a given lookup.

        """
        self._clear_index()
        video1 = self.create_video(name='Video1', update_index=False)
        video2 = self.create_video(name='Video2', update_index=False)
        video3 = self.create_video(name='Video3', update_index=False)
        video4 = self.create_video(name='Video4', update_index=False)
        self.create_watch(video2, days=5)
        self.create_watch(video3, days=7)
        self.create_watch(video4, days=9)
        expected = set()
        results = set((r.pk for r in SearchQuerySet()))
        self.assertEqual(results, expected)

        now = datetime.now()
        six_days_ago = now - timedelta(6)
        eight_days_ago = now - timedelta(8)

        haystack_batch_update.apply(args=(Video._meta.app_label,
                                          Video._meta.module_name),
                                    kwargs={'start': six_days_ago,
                                            'date_lookup': 'watch__timestamp'})
        expected = set((video2.pk,))
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)

        self._clear_index()

        haystack_batch_update.apply(args=(Video._meta.app_label,
                                          Video._meta.module_name),
                                    kwargs={'end': six_days_ago,
                                            'date_lookup': 'watch__timestamp'})
        expected = set((video3.pk, video4.pk))
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)

        self._clear_index()


        with override_settings(DEBUG=True):
            haystack_batch_update.apply(args=(Video._meta.app_label,
                                              Video._meta.module_name),
                                        kwargs={'start': eight_days_ago,
                                                'end': six_days_ago,
                                                'date_lookup': 'watch__timestamp'})
            queries = connections['default'].queries
            # The query here shouldn't use the index queryset as its base.
            # If it did, it'll have an OUTER JOIN in it.
            self.assertFalse('OUTER JOIN' in queries[0]['sql'])
        expected = set((video3.pk,))
        results = set((int(r.pk) for r in SearchQuerySet()))
        self.assertEqual(results, expected)

    def test_remove(self):
        """
        ``remove`` kwarg should be passed on to the batches.

        """
        self._clear_index()
        video1 = self.create_video(name='Video1', update_index=False)
        def get_remove_passed(sender, **kwargs):
            self.assertTrue('remove' in kwargs['kwargs'])
            self.remove = kwargs['kwargs']['remove']
        task_postrun.connect(get_remove_passed, sender=haystack_update)

        expected = True
        haystack_batch_update.apply(args=(Video._meta.app_label,
                                          Video._meta.module_name),
                                    kwargs={'remove': expected})
        self.assertEqual(self.remove, expected)

        expected = False
        haystack_batch_update.apply(args=(Video._meta.app_label,
                                          Video._meta.module_name),
                                    kwargs={'remove': expected})
        self.assertEqual(self.remove, expected)

    def test_distinct_pks(self):
        self._clear_index()
        video1 = self.create_video(name='Video1', update_index=False)
        self.create_watch(video1, days=5)
        self.create_watch(video1, days=3)
        self.create_watch(video1, days=2)
        six_days_ago = datetime.now() - timedelta(6)

        with mock.patch.object(haystack_update, 'delay') as delay:
            haystack_batch_update.apply(args=(Video._meta.app_label,
                                              Video._meta.module_name),
                                        kwargs={'start': six_days_ago,
                                                'date_lookup': 'watch__timestamp'})
            delay.assert_called_once_with(Video._meta.app_label,
                                          Video._meta.module_name,
                                          [video1.pk], using='default', remove=True)


class VideoSaveThumbnailTestCase(BaseTestCase):
    def test_thumbnail_not_200(self):
        """
        If a video's thumbnail url returns a non-200 status code, the task
        should be retried.

        """
        thumbnail_url = 'http://pculture.org/not'
        video = self.create_video(update_index=False, has_thumbnail=True,
                                  thumbnail_url=thumbnail_url)

        class MockException(Exception):
            pass

        with mock.patch('localtv.tasks.urllib.urlopen') as urlopen:
            with mock.patch.object(video_save_thumbnail, 'retry',
                                   side_effect=MockException):
                self.assertRaises(MockException,
                                  video_save_thumbnail.apply,
                                  args=(video.pk,))
                urlopen.assert_called_once_with(thumbnail_url)
        new_video = Video.objects.get(pk=video.pk)
        self.assertEqual(new_video.has_thumbnail, video.has_thumbnail)
        self.assertEqual(new_video.thumbnail_url, video.thumbnail_url)

    def test_data_saved(self):
        """
        The thumbnail data for a video should be saved once this task is
        completed.

        """
        thumbnail_url = 'http://pculture.org/not'
        video = self.create_video(update_index=False, has_thumbnail=True,
                                  thumbnail_url=thumbnail_url)
        thumbnail_data = self._data_file('logo.png').read()
        remote_file = mock.Mock(read=lambda: thumbnail_data,
                                getcode=lambda: 200)
        with mock.patch('localtv.tasks.urllib.urlopen',
                        return_value=remote_file):
            video_save_thumbnail.apply(args=(video.pk,))
        new_video = Video.objects.get(pk=video.pk)
        self.assertEqual(new_video.has_thumbnail, True)
        self.assertEqual(new_video.thumbnail_url, thumbnail_url)
        self.assertEqual(new_video.thumbnail_extension, 'png')
