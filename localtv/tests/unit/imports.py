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

from celery.signals import task_postrun
from haystack.query import SearchQuerySet
from vidscraper.suites import Video

from localtv.models import Source, FeedImport
from localtv.tasks import haystack_update, haystack_remove
from localtv.tests.base import BaseTestCase


class FeedImportUnitTestCase(BaseTestCase):
    def create_vidscraper_video(self, url='http://youtube.com/watch/?v=fake',
                                loaded=True, embed_code='hi', title='Test',
                                **field_data):
        video = Video(url)
        video._loaded = loaded
        field_data.update({'embed_code': embed_code, 'title': title})
        for key, value in field_data.items():
            setattr(video, key, value)

        return video

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
