from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import Http404

from localtv.listing.views import CompatibleListingView
from localtv.models import Video, Category
from localtv.search.utils import NormalizedVideoList
from localtv.search.views import SortFilterView
from localtv.tests import BaseTestCase
from localtv.views import VideoView


class VideoViewTestCase(BaseTestCase):
    def test_get_queryset(self):
        """The queryset should be this site's active videos."""
        site1 = Site.objects.get_current()
        site2 = Site.objects.create(name='test', domain='test.com')
        video1 = self.create_video(site_id=site1.pk)
        video2 = self.create_video(site_id=site1.pk)
        self.create_video(status=Video.NEEDS_MODERATION)
        self.create_video(site_id=site2.pk)

        view = VideoView()
        view.request = self.factory.get('/')
        results = set(view.get_queryset())
        self.assertEqual(results, set((video1, video2)))

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
                        [video1, video2, video3, video5])

    def test_unicode_name(self):
        name = u'\u1015\u103c\u1031\u102c\u1004\u103a\u1038\u200b\u1016\u1030\u1038\u200b\u1000\u103c\u1031\u102c\u103a\u200b\u101b\u200b\u1021\u1031\u102c\u1004\u103a\u200b'
        slug = u'\u1015\u1004\u1016\u1000\u101b\u1021\u1004'
        video = self.create_video(name)
        view = VideoView()
        view.request = self.factory.get(video.get_absolute_url())
        view.kwargs = {'slug': slug, 'video_id': video.pk}
        response = view.get(view.request)
        self.assertEqual(response.status_code, 200)


class CompatibleListingViewTestCase(BaseTestCase):
    def test_paginate_by(self):
        """
        Compatible listing views support the 'count' parameter to modify
        pagination.

        """
        view = CompatibleListingView()
        view.request = self.factory.get('/', {'count': 1})
        self.assertEqual(view.get_paginate_by(None), 1)

    def test_get_form_data(self):
        """
        Compatible listing views support 'query' as an alterative to 'q'
        iff 'q' is not also supplied, and allow 'latest' as an alias for
        'newest'.

        """
        view = CompatibleListingView()
        data = view.get_form_data({'query': 'foo'})
        self.assertEqual(data.get('q'), 'foo')

        data = view.get_form_data({'query': 'foo', 'q': 'bar'})
        self.assertEqual(data.get('q'), 'bar')

        data = view.get_form_data({'sort': 'latest'})
        self.assertEqual(data.get('sort'), 'newest')

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
        Compatible listing views should include 'query' and 'video_list'.

        """
        view = CompatibleListingView()
        view.request = self.factory.get('/')
        view.kwargs = {}
        context = view.get_context_data(object_list=view.get_queryset())
        self.assertTrue('query' in context)
        self.assertTrue('video_list' in context)
        for f in context['form'].filter_fields():
            self.assertFalse(f.name in context)


class SortFilterViewTestCase(BaseTestCase):
    def test_get_object(self):
        view = SortFilterView()
        view.request = self.factory.get('/')
        view.kwargs = {'pk': 1}
        view.filter_name = 'author'
        self.assertRaises(Http404, view.get_object)
        view.kwargs = {'pk': 'foo'}
        self.assertRaises(Http404, view.get_object)

    def test_get_context_data(self):
        """
        The SortFilterView should provide 'videos', 'form', and, if relevant,
        the current enforced filter object.

        """
        view = SortFilterView()
        category = self.create_category()
        view.request = self.factory.get('/')
        view.kwargs = {'slug': category.slug}
        view.filter_name = 'category'
        view.filter_kwarg = 'slug'
        view.object = view.get_object()
        context = view.get_context_data(object_list=view.get_queryset())
        self.assertEqual(context['category'], category)
        self.assertTrue('videos' in context)
        self.assertTrue('form' in context)

    def test_invalid_sort(self):
        """
        If an invalid sort is selected, should fall back on the "newest" sort.

        """
        self._clear_index()
        for i in range(3):
            self.create_video('test' + str(i))
        view = SortFilterView()
        view.request = self.factory.get('/', {'sort': 'unheard_of'})
        self.assertFalse(hasattr(view, 'form'))
        queryset = view.get_queryset()
        self.assertEqual(len(queryset), 3)
        self.assertTrue(hasattr(view, 'form'))
        self.assertEqual(view.form.cleaned_data['sort'], 'newest')

    def test_invalid_filter_value(self):
        """
        If an invalid filter value is provided, an empty queryset should be
        returned.

        """
        view = SortFilterView()
        view.filter_name = 'category'
        view.filter_kwarg = 'slug'
        self.assertRaises(Category.DoesNotExist,
                          Category.objects.get,
                          slug__iexact='test')
        view.kwargs = {'slug': 'test'}
        view.request = self.factory.get('/')
        queryset = view.get_queryset()
        self.assertEqual(len(queryset), 0)

    def test_iexact_filter_value(self):
        """
        If a filter value of incorrect case is provided, the user should be
        redirected to the absolute url of the object.

        """
        category = self.create_category(slug='test')
        url = reverse('localtv_category', kwargs={'slug': 'Test'})
        real_url = reverse('localtv_category', kwargs={'slug': 'test'})
        self.assertEqual(category.get_absolute_url(), real_url)

        view = SortFilterView()
        view.filter_name = 'category'
        view.filter_kwarg = 'slug'
        view.request = self.factory.get(url)
        view.kwargs = {'slug': 'Test'}
        response = view.get(view.request, **view.kwargs)
        self.assertRedirects(response, real_url, netloc='')
