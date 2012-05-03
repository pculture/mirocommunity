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
from django.http import Http404

from localtv.listing.views import CompatibleListingView
from localtv.models import Video
from localtv.search.utils import NormalizedVideoList
from localtv.search.views import SortFilterView
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


class CompatibleListingViewTestCase(BaseTestCase):
    def test_paginate_by(self):
        """
        Compatible listing views support the 'count' parameter to modify
        pagination.

        """
        view = CompatibleListingView()
        view.request = self.factory.get('/', {'count': 1})
        self.assertEqual(view.get_paginate_by(None), 1)

    def test_query_param(self):
        """
        Compatible listing views support 'query' as an alterative to 'q'
        iff 'q' is not also supplied.

        """
        view = CompatibleListingView()
        view.request = self.factory.get('/', {'query': 'foo'})
        view.kwargs = {}
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['data'].get('q'), 'foo')

        view.request = self.factory.get('/', {'query': 'foo', 'q': 'bar'})
        view.kwargs = {}
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['data'].get('q'), 'bar')

    def test_queryset(self):
        """
        Compatible listing views must return normalized querysets.

        """
        view = CompatibleListingView()
        view.request = self.factory.get('/')
        view.kwargs = {}
        self.assertTrue(isinstance(view.get_queryset(), NormalizedVideoList))

    def test_get_context_data(self):
        """
        Compatible listing views should include 'query', 'video_list', and
        (if relevant) the current filter object in the context data.

        """
        view = CompatibleListingView()
        view.request = self.factory.get('/')
        view.kwargs = {}
        context = view.get_context_data(object_list=view.get_queryset())
        self.assertTrue('query' in context)
        self.assertTrue('video_list' in context)
        for f in context['form'].filter_fields():
            self.assertFalse(f.name in context)

        category = self.create_category()
        view.request = self.factory.get('/')
        view.kwargs = {'slug': category.slug}
        view.url_filter = 'category'
        view.url_filter_kwarg = 'slug'
        context = view.get_context_data(object_list=view.get_queryset())
        self.assertEqual(context['category'], category)


class SortFilterViewTestCase(BaseTestCase):
    def test_queryset(self):
        view = SortFilterView()
        view.request = self.factory.get('/')
        view.kwargs = {'pk': 1}
        view.url_filter = 'author'
        self.assertRaises(Http404, view.get_queryset)
