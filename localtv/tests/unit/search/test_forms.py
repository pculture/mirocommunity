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

from localtv.models import Video
from localtv.search.forms import DateTimeFilterField, SearchForm
from localtv.tests import BaseTestCase


class DateTimeFilterFieldTestCase(BaseTestCase):
    def setUp(self):
        self._clear_index()
        self.field = DateTimeFilterField(field_lookups=('last_featured',),
                                         label='')
        # We create the video which was never featured first because of whoosh
        # bug #263.
        # https://bitbucket.org/mchaput/whoosh/issue/263
        self.video1 = self.create_video(name='video1')
        # Backwards-compatibility check: also exclude max datetimes.
        self.video0 = self.create_video(name='video0',
                            last_featured=datetime.max)
        self.video0.last_featured = None
        self.video0.save(update_index=False)
        self.video2 = self.create_video(name='video2',
                            last_featured=datetime.now() - timedelta(1))
        self.video3 = self.create_video(name='video3',
                            last_featured=datetime.now())
        self.video4 = self.create_video(name='video4',
                            last_featured=datetime.now() - timedelta(2))

    def test_filter__on(self):
        expected = set((self.video2.pk, self.video3.pk, self.video4.pk))

        results = set(v.pk
                    for v in self.field.filter(Video.objects.all(), True))
        self.assertEqual(results, expected)

        results = set(int(r.pk)
                    for r in self.field.filter(SearchQuerySet(), True))
        self.assertEqual(results, expected)

    def test_filter__off(self):
        expected = set((self.video2.pk, self.video3.pk, self.video4.pk,
                        self.video1.pk, self.video0.pk))

        results = set(v.pk
                    for v in self.field.filter(Video.objects.all(), False))
        self.assertEqual(results, expected)

        results = set(int(r.pk)
                    for r in self.field.filter(SearchQuerySet(), False))
        self.assertEqual(results, expected)


class SearchFormTestCase(BaseTestCase):
    def test_invalid_sort(self):
        """
        An invalid sort should be replaced during cleaning with the default
        sort, rather than causing the entire form to become invalid.

        """
        form = SearchForm({'sort': 'asdf', 'q': 'q'})
        self.assertFalse('asdf' in form.fields['sort'].choices)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['sort'], form.fields['sort'].initial)
