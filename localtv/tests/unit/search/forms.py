from datetime import datetime, timedelta

from haystack.query import SearchQuerySet

from localtv.models import Video
from localtv.search.forms import DateTimeFilterField, SearchForm
from localtv.tests.base import BaseTestCase


class DateTimeFilterFieldTestCase(BaseTestCase):
    def setUp(self):
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
