import itertools
import operator

from django.db.models.query import Q
from django.utils.translation import ugettext_lazy as _
from haystack import connections
from haystack.backends import SQ
from haystack.query import SearchQuerySet

from localtv.models import SiteSettings, Video


EMPTY = object()


def _exact_q(queryset, field, value):
    # Returns a Q or SQ instance representing an __exact query for the given
    # field/value. This facilitates a HACK necessitated by Whoosh __exact
    # queries working strangely.
    # https://github.com/toastdriven/django-haystack/issues/529
    q_class = SQ if isinstance(queryset, SearchQuerySet) else Q
    if value is None:
        return q_class(**{'{0}__isnull'.format(field): True})
    if (q_class is SQ and
       'WhooshEngine' in
       connections[queryset.query._using].options['ENGINE']):
        return q_class(**{field: value})
    return q_class(**{'{0}__exact'.format(field): value})


def _in_q(queryset, field, values):
    # Returns a Q or SQ instance representing an __in query for the given
    # field/value. This facilitates a HACK necessitated by Whoosh, which
    # doesn't properly support __in with multiple values. Instead, we
    # calculate each value separately and OR them together.
    q_class = SQ if isinstance(queryset, SearchQuerySet) else Q
    if (q_class is SQ and
        'WhooshEngine' in
        connections[queryset.query._using].options['ENGINE']):
        qs = [_exact_q(queryset, field, value) for value in values]
        return reduce(operator.or_, qs)
    return q_class(**{'{0}__in'.format(field): values})


def _q_for_queryset(queryset, field, values):
    if len(values) == 1:
        return _exact_q(queryset, field, values[0])
    else:
        return _in_q(queryset, field, values)


class NormalizedVideoList(object):
    """
    Wraps either a haystack :class:`SearchQuerySet` or a django
    :class:`QuerySet` and provides normalized access to the objects as
    efficiently as possible.

    """
    def __init__(self, queryset, select_related=None, prefetch_related=None):
        select_related = (['feed', 'user', 'search']
                          if select_related is None else select_related)
        prefetch_related = (['authors']
                            if prefetch_related is None else prefetch_related)

        self.is_haystack = isinstance(queryset, SearchQuerySet)
        if self.is_haystack:
            if 'WhooshEngine' in connections[queryset.query._using
                                             ].options['ENGINE']:
                # Workaround for django-haystack #574.
                # https://github.com/toastdriven/django-haystack/issues/574
                list(queryset)
        else:
            queryset = queryset.select_related(*select_related)
            queryset = queryset.prefetch_related(*prefetch_related)

        self.queryset = queryset
        self.select_related = select_related
        self.prefetch_related = prefetch_related

    def __getitem__(self, k):
        if self.is_haystack:
            results = self.queryset[k]
            if isinstance(results, list):
                pks = [r.pk for r in results]
                qs = Video.objects.filter(status=Video.ACTIVE)
                qs = qs.select_related(*self.select_related)
                qs = qs.prefetch_related(*self.prefetch_related)
                video_dict = qs.in_bulk(pks)
                videos = []
                for r in results:
                    if r.pk not in video_dict:
                        try:
                            pk = int(r.pk)
                        except ValueError:
                            pass
                    try:
                        video = video_dict[pk]
                    except KeyError:
                        continue
                    video.watch_count = r.watch_count or 0
                    videos.append(video_dict[pk])
                return videos
            if results is not None:
                return results.object
            raise IndexError
        else:
            return self.queryset[k]

    def __len__(self):
        return len(self.queryset)

    def __iter__(self):
        if self.is_haystack:
            return iter(result.object for result in self.queryset
                        if result is not None)
        else:
            return iter(self.queryset)


class Sort(object):
    """
    Class representing a sort which can be performed on a :class:`QuerySet` or
    :class:`SearchQuerySet` and the methods which make that sort work.

    :param descending: Whether the sort should be descending (default) or not.
    :param verbose_name: A human-readable name for this sort.
    :param field_lookup: The field lookup which will be used in the sort
                         query.

    """
    def __init__(self, verbose_name, field_lookup, descending=True):
        self.verbose_name = verbose_name
        self.descending = descending
        self.field_lookup = field_lookup

    def sort(self, queryset):
        """
        Does the actual ordering.

        """
        return queryset.order_by(self.get_order_by(queryset))

    def get_field_lookup(self, queryset):
        """
        Returns the field which will be sorted on. By default, returns the value
        of :attr:`field_lookup`.

        """
        return self.field_lookup

    def get_order_by(self, queryset):
        """Performs the actual ordering for the :class:`Sort`."""
        return ''.join(('-' if self.descending else '',
                        self.get_field_lookup(queryset)))


class DummySort(Sort):
    """Looks like a sort, but does nothing."""
    def __init__(self, verbose_name):
        self.verbose_name = verbose_name

    def sort(self, queryset):
        return queryset


class BestDateSort(Sort):
    def __init__(self, verbose_name=None, descending=True):
        if verbose_name is None:
            verbose_name = _('Newest') if descending else _('Oldest')
        super(BestDateSort, self).__init__(verbose_name, None,
                                           descending)

    def get_field_lookup(self, queryset):
        if (isinstance(queryset, SearchQuerySet) and
            SiteSettings.objects.get_current().use_original_date):
            return 'best_date_with_published'
        return 'best_date'

    def sort(self, queryset):
        if not isinstance(queryset, SearchQuerySet):
            queryset = queryset.with_best_date(
                           SiteSettings.objects.get_current().use_original_date)
        return super(BestDateSort, self).sort(queryset)


class PopularSort(Sort):
    def __init__(self, verbose_name=_('Popular'), descending=True):
        super(PopularSort, self).__init__(verbose_name, 'watch_count',
                                          descending)

    def sort(self, queryset):
        if not isinstance(queryset, SearchQuerySet):
            popular = queryset.popular()
            not_popular = queryset.not_popular()
            return itertools.chain(popular, not_popular)
        return super(PopularSort, self).sort(queryset)
