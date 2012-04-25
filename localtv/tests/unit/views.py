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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from localtv.models import Video
from localtv.tests.base import BaseTestCase
from localtv.views import VideoView


class VideoViewTestCase(BaseTestCase):
    def test_get_queryset(self):
        """The queryset should be this site's active videos."""
        video1 = self.create_video(site_id=settings.SITE_ID)
        video2 = self.create_video(site_id=settings.SITE_ID)
        self.create_video(status=Video.UNAPPROVED)
        self.create_video(site_id=settings.SITE_ID + 1)

        view = VideoView()
        view.request = self.factory.get('/')
        results = set(view.get_queryset())
        self.assertEqual(results, set((video1, video2)))

        # TODO: Test for admins as well - this would replace
        # test_view_video_admins_see_rejected

    def test_context__category(self):
        """
        If the video has categories, the VideoView should include a category
        in its context_data and limit the provided popular videos to that
        category.

        """
        category = self.create_category(name='Category')
        video1 = self.create_video('test1', watches=5, categories=[category])
        video2 = self.create_video('test2', watches=4, categories=[category])
        video3 = self.create_video('test3', watches=3, categories=[category])
        video4 = self.create_video('test4', watches=20)
        video5 = self.create_video('test5', watches=0, categories=[category])

        view = VideoView()
        view.request = self.factory.get('/')
        view.object = video1
        context = view.get_context_data(object=video1)
        self.assertEqual(context['category'].pk, category.pk)
        self.assertEqual(list(context['popular_videos']),
                        [video1, video2, video3])
