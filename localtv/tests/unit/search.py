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

from haystack.query import SearchQuerySet

from localtv.models import Video, SiteLocation
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
        self.video2 = self.create_video(name="%s - %s" % (date3.strftime(f),
                                                          date3.strftime(f)),
                                        when_approved=date3,
                                        when_published=date3)
        self.sort = utils.BestDateSort()
        self.site_location = SiteLocation.objects.get_current()

    def test_get_field(self):
        """
        The database version coalesces an extra best_date field for sorting; the
        haystack version has an additional index field for when
        ``use_original_date`` is ``True``.

        """
        self.site_location.use_original_date = True
        self.site_location.save()
        self.assertEqual(self.sort.get_field(SearchQuerySet()),
                         'best_date_with_published')
        self.assertEqual(self.sort.get_field(Video.objects.all()),
                         'best_date')

        self.site_location.use_original_date = False
        self.site_location.save()
        self.assertEqual(self.sort.get_field(SearchQuerySet()),
                         'best_date')
        self.assertEqual(self.sort.get_field(Video.objects.all()),
                         'best_date')

    def test_sort(self):
        """
        Checks that the sorted queryset is actually correctly sorted.

        """
        def key_with_original(v):
            v = getattr(v, 'object', v)
            return v.when_published or v.when_approved or v.when_submitted

        def key_without_original(v):
            v = getattr(v, 'object', v)
            return v.when_approved or v.when_submitted

        self.site_location.use_original_date = True
        self.site_location.save()
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

        self.site_location.use_original_date = False
        self.site_location.save()
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
