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

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from haystack.query import SearchQuerySet

from localtv.models import Video, SiteSettings, Category
from localtv.search import utils
from localtv.tests.base import BaseTestCase


class NormalizedVideoListUnitTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self._clear_index()
        self.create_video()
        self.create_video()
        self.create_video(status=Video.UNAPPROVED)
        self.nvl1 = utils.NormalizedVideoList(
                            Video.objects.filter(status=Video.ACTIVE))
        self.nvl2 = utils.NormalizedVideoList(
                            SearchQuerySet().models(Video).filter(site=1))

    def test_getitem(self):
        """
        __getitem__ should return a list of Video instances when passed a slice
        and a single Video when passed an integer.

        """
        self.assertTrue(all(isinstance(v, Video) for v in self.nvl1[:]))
        self.assertTrue(isinstance(self.nvl1[0], Video))

        self.assertTrue(all(isinstance(v, Video) for v in self.nvl2[:]))
        self.assertTrue(isinstance(self.nvl2[0], Video))

    def test_len(self):
        """
        __len__ should return the length of the video list.

        """
        self.assertEqual(len(self.nvl1), 2)
        self.assertEqual(len(self.nvl2), 2)

    def test_iter(self):
        """
        Iterating over a NormalizedVideoList should yield video instances.

        """
        self.assertTrue(all(isinstance(v, Video) for v in self.nvl1))
        self.assertTrue(all(isinstance(v, Video) for v in self.nvl2))


class BestDateSortUnitTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self._clear_index()
        date1_1 = datetime.now() - timedelta(7)
        date1_2 = datetime.now() - timedelta(1)
        date2 = datetime.now()
        date3 = datetime.now() - timedelta(3)
        f = "%Y/%m/%d"
        self.video1 = self.create_video(name="%s - %s" % (date1_1.strftime(f),
                                                          date1_2.strftime(f)),
                                        when_approved=date1_1,
                                        when_published=date1_2)
        self.video2 = self.create_video(name="%s - %s" % (date2.strftime(f),
                                                          date2.strftime(f)),
                                        when_approved=date2,
                                        when_published=date2)
        self.video3 = self.create_video(name="%s - %s" % (date3.strftime(f),
                                                          date3.strftime(f)),
                                        when_approved=date3,
                                        when_published=date3)
        self.sort = utils.BestDateSort()
        self.site_settings = SiteSettings.objects.get_current()

    def test_sort(self):
        """
        Checks that the sorted queryset is actually correctly sorted.

        """
        def key_with_original(v):
            return v.when_published or v.when_approved or v.when_submitted

        def key_without_original(v):
            return v.when_approved or v.when_submitted

        self.site_settings.use_original_date = True
        self.site_settings.save()
        expected_asc = sorted(list(Video.objects.all()), key=key_with_original)
        expected_desc = sorted(list(Video.objects.all()), key=key_with_original,
                               reverse=True)

        results = list(self.sort.sort(Video.objects.all()))
        self.assertEqual(results, expected_asc)
        results = [r.object for r in self.sort.sort(SearchQuerySet())]
        self.assertEqual(results, expected_asc)

        results = list(self.sort.sort(Video.objects.all(), descending=True))
        self.assertEqual(results, expected_desc)
        results = [r.object for r in self.sort.sort(SearchQuerySet(),
                                                    descending=True)]
        self.assertEqual(results, expected_desc)

        self.site_settings.use_original_date = False
        self.site_settings.save()
        expected_asc = sorted(list(Video.objects.all()),
                              key=key_without_original)
        expected_desc = sorted(list(Video.objects.all()),
                               key=key_without_original,
                               reverse=True)

        results = list(self.sort.sort(Video.objects.all()))
        self.assertEqual(results, expected_asc)
        results = [r.object for r in self.sort.sort(SearchQuerySet())]
        self.assertEqual(results, expected_asc)

        results = list(self.sort.sort(Video.objects.all(), descending=True))
        self.assertEqual(results, expected_desc)
        results = [r.object for r in self.sort.sort(SearchQuerySet(),
                                                    descending=True)]
        self.assertEqual(results, expected_desc)


class FeaturedSortUnitTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self._clear_index()
        date1 = datetime.now() - timedelta(7)
        date2 = datetime.now()
        date3 = datetime.now() - timedelta(3)
        f = "%Y/%m/%d"
        self.video1 = self.create_video(name=date1.strftime(f),
                                        last_featured=date1)
        self.video2 = self.create_video(name=date2.strftime(f),
                                        last_featured=date2)
        self.video3 = self.create_video(name=date3.strftime(f),
                                        last_featured=date3)
        self.video4 = self.create_video(name='None', last_featured=None)
        self.sort = utils.FeaturedSort()

    def test_sort(self):
        """
        Checks that the sorted queryset is actually correctly sorted, and that
        videos without a last_featured date are excluded.

        """
        all_videos = [self.video1, self.video2, self.video3]
        expected_asc = sorted(all_videos, key=lambda v: v.last_featured)
        expected_desc = sorted(all_videos, key=lambda v: v.last_featured,
                               reverse=True)

        results = list(self.sort.sort(Video.objects.all()))
        self.assertEqual(results, expected_asc)
        results = [r.object for r in self.sort.sort(SearchQuerySet())]
        self.assertEqual(results, expected_asc)

        results = list(self.sort.sort(Video.objects.all(), descending=True))
        self.assertEqual(results, expected_desc)
        results = [r.object for r in self.sort.sort(SearchQuerySet(),
                                                    descending=True)]
        self.assertEqual(results, expected_desc)


class ApprovedSortUnitTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self._clear_index()
        date1 = datetime.now() - timedelta(7)
        date2 = datetime.now()
        date3 = datetime.now() - timedelta(3)
        f = "%Y/%m/%d"
        self.video1 = self.create_video(name=date1.strftime(f),
                                        when_approved=date1)
        self.video2 = self.create_video(name=date2.strftime(f),
                                        when_approved=date2)
        self.video3 = self.create_video(name=date3.strftime(f),
                                        when_approved=date3)
        self.video4 = self.create_video(name='None', when_approved=None)
        self.sort = utils.ApprovedSort()

    def test_sort(self):
        """
        Checks that the sorted queryset is actually correctly sorted, and that
        videos without a when_approved date are excluded.

        """
        all_videos = [self.video1, self.video2, self.video3]
        expected_asc = sorted(all_videos, key=lambda v: v.when_approved)
        expected_desc = sorted(all_videos, key=lambda v: v.when_approved,
                               reverse=True)

        results = list(self.sort.sort(Video.objects.all()))
        self.assertEqual(results, expected_asc)
        results = [r.object for r in self.sort.sort(SearchQuerySet())]
        self.assertEqual(results, expected_asc)

        results = list(self.sort.sort(Video.objects.all(), descending=True))
        self.assertEqual(results, expected_desc)
        results = [r.object for r in self.sort.sort(SearchQuerySet(),
                                                    descending=True)]
        self.assertEqual(results, expected_desc)


class PopularSortUnitTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self._clear_index()
        self.video0 = self.create_video(name="0 watches", watches=0)
        self.video2 = self.create_video(name="2 watches", watches=2)
        self.video1 = self.create_video(name="1 watch", watches=1)
        self.video3 = self.create_video(name="3 watches", watches=3)
        self.sort = utils.PopularSort()

    def test_sort(self):
        """
        Checks that the sorted queryset is actually sorted by watch count, and
        that videos with no watches are excluded.

        """
        all_videos = [self.video1, self.video2, self.video3]
        expected_asc = sorted(all_videos, key=lambda v: v.watch_set.count())
        expected_desc = sorted(all_videos, key=lambda v: v.watch_set.count(),
                               reverse=True)

        results = list(self.sort.sort(Video.objects.all()))
        self.assertEqual(results, expected_asc)
        results = [r.object for r in self.sort.sort(SearchQuerySet())]
        self.assertEqual(results, expected_asc)

        results = list(self.sort.sort(Video.objects.all(), descending=True))
        self.assertEqual(results, expected_desc)
        results = [r.object for r in self.sort.sort(SearchQuerySet(),
                                                    descending=True)]
        self.assertEqual(results, expected_desc)


class ModelFilterUnitTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self._clear_index()
        Site.objects.create(name='example.com', domain='example.com')
        self.user_filter = utils.ModelFilter(('authors', 'user'), User)
        self.category_filter = utils.ModelFilter(('categories',), Category,
                                                 field='slug')
        self.user1 = self.create_user(username='user1')
        self.user2 = self.create_user(username='user2')
        self.category1 = self.create_category(name='category1')
        self.category2 = self.create_category(name='category2')
        self.category3 = self.create_category(name='category3', site_id=2)
        self.video1 = self.create_video(name='user1,category1', user=self.user1,
                                        categories=[self.category1])
        self.video2 = self.create_video(name='user1,category2',
                                        authors=[self.user1],
                                        categories=[self.category2])
        self.video3 = self.create_video(name='user2,category1',
                                        authors=[self.user2],
                                        categories=[self.category1])
        self.video4 = self.create_video(name='user2,category2', user=self.user2,
                                        categories=[self.category2])
        self.video5 = self.create_video(name='user1-2,category1-2',
                                        authors=[self.user1, self.user2],
                                        categories=[self.category1,
                                                    self.category2])
        self.video6 = self.create_video(name='category3',
                                        categories=[self.category3])

    def test_clean_filter_values(self):
        """
        Cleaned filter values should always be a list, tuple, or queryset of
        model instances of the correct type.

        """
        # clean users (pk-based clean)
        expected = [self.user1]

        results = self.user_filter.clean_filter_values([self.user1])
        self.assertEqual(list(results), expected)

        results = self.user_filter.clean_filter_values(
                            User.objects.filter(pk__in=[self.user1.pk]))
        self.assertEqual(list(results), expected)

        results = self.user_filter.clean_filter_values([self.user1.pk])
        self.assertEqual(list(results), expected)

        # clean categories (slug-based clean)
        expected = [self.category1]

        results = self.category_filter.clean_filter_values([self.category1])
        self.assertEqual(list(results), expected)

        results = list(self.category_filter.clean_filter_values(
                            Category.objects.filter(pk__in=[self.category1.pk])))
        self.assertEqual(list(results), expected)

        results = self.category_filter.clean_filter_values(
                            [self.category1.slug])
        self.assertEqual(list(results), expected)

        # clean categories (exclude categories for other sites)
        results = self.category_filter.clean_filter_values(
                            [self.category1.slug, self.category3.slug])

    def test_filter(self):
        """
        Given a queryset and an iterable of model instances, returns a queryset
        of videos which have any of those model instances attached to them.

        """
        # filtered on multiple...
        expected = set((self.video1, self.video2, self.video3, self.video4,
                       self.video5))

        # filtered on multiple users
        users = [self.user1, self.user2]
        filtered = self.user_filter.filter(Video.objects.all(), users)
        self.assertEqual(set(filtered), expected)

        filtered = self.user_filter.filter(SearchQuerySet(), users)
        self.assertEqual(set(r.object for r in filtered), expected)

        # filtered on multiple categories
        categories = [self.category1, self.category2]
        filtered = self.category_filter.filter(Video.objects.all(), categories)
        self.assertEqual(set(filtered), expected)

        filtered = self.category_filter.filter(SearchQuerySet(), categories)
        self.assertEqual(set(r.object for r in filtered), expected)

        # filtered on one user
        users = [self.user1]
        expected = set((self.video1, self.video2, self.video5))
        filtered = self.user_filter.filter(Video.objects.all(), [self.user1])
        self.assertEqual(set(filtered), expected)

        filtered = self.user_filter.filter(SearchQuerySet(), users)
        self.assertEqual(set(r.object for r in filtered), expected)

        # filtered on one category
        categories = [self.category1]
        expected = set((self.video1, self.video3, self.video5))
        filtered = self.category_filter.filter(Video.objects.all(), categories)
        self.assertEqual(set(filtered), expected)

        filtered = self.category_filter.filter(SearchQuerySet(), categories)
        self.assertEqual(set(r.object for r in filtered), expected)

    def test_formfield(self):
        """
        The formfield for a model filter is a queryset of all instances, or all
        instances associated with the current site, if relevant.

        """
        expected = set((self.user1, self.user2))
        formfield = self.user_filter.formfield()
        self.assertEqual(set(formfield.queryset), expected)

        expected = set((self.category1, self.category2))
        formfield = self.category_filter.formfield()
        self.assertEqual(set(formfield.queryset), expected)


class TagFilterUnitTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self._clear_index()
        self.filter = utils.TagFilter(('tags',))
        self.site2 = Site.objects.create(name='example.com', domain='example.com')
        self.tag1 = self.create_tag(name='tag1')
        self.tag2 = self.create_tag(name='tag2')
        self.tag3 = self.create_tag(name='tag3')
        self.tag4 = self.create_tag(name='tag4')
        self.tag5 = self.create_tag(name='tag5')
        self.video1 = self.create_video(name='tags1-2', tags='tag1 tag2')
        self.video2 = self.create_video(name='tags1-3', tags='tag1 tag3')
        self.video3 = self.create_video(name='tags1-2-3', tags='tag1 tag2 tag3')
        self.video4 = self.create_video(name='tag3', tags='tag3')
        self.video5 = self.create_video(name='tag4', tags='tag4',
                                        status=Video.UNAPPROVED)
        self.video6 = self.create_video(name='tag4_2', tags='tag4', site_id=2)

    def test_clean_filter_values(self):
        """
        Cleaned values should be a list, queryset, or tuple of Tag instances.
        Valid inputs are:

        * single Tag instance.
        * list or tuple of tag instances.
        * list or tuple of tag names.
        * list or tuple of tag primary keys.
        * string representing tags.

        This is because we are using django-tagging's get_tag_list utility to
        do the cleaning.

        """
        expected = set((self.tag1, self.tag2))
        results = set(self.filter.clean_filter_values('tag1 tag2'))
        self.assertEqual(results, expected)

        results = set(self.filter.clean_filter_values([self.tag1, self.tag2]))
        self.assertEqual(results, expected)

        results = set(self.filter.clean_filter_values([self.tag1.name,
                                                       self.tag2.name]))
        self.assertEqual(results, expected)

        results = set(self.filter.clean_filter_values([self.tag1.pk,
                                                       self.tag2.pk]))
        self.assertEqual(results, expected)

        expected = set((self.tag3,))
        results = set(self.filter.clean_filter_values('tag3'))
        self.assertEqual(results, expected)

        results = set(self.filter.clean_filter_values(self.tag3))
        self.assertEqual(results, expected)

    def test_filter(self):
        """
        Given a queryset and an iterable of Tag instances, returns a queryset
        of videos which have any of those tags.

        """
        expected = set((self.video1, self.video2, self.video3))

        tags = [self.tag1, self.tag2]
        results = self.filter.filter(Video.objects.all(), tags)
        self.assertEqual(set(results), expected)

        results = self.filter.filter(SearchQuerySet(), tags)
        self.assertEqual(set(r.object for r in results), expected)

    def test_formfield(self):
        """
        The formfield for a TagFilter should hold a queryset of all tags which
        are used on active videos for the current site.

        """
        expected = set((self.tag1, self.tag2, self.tag3))
        formfield = self.filter.formfield()
        self.assertEqual(set(formfield.queryset), expected)
