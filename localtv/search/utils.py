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

import operator

from django import forms
from django.contrib.sites.models import Site
from django.db.models.fields import FieldDoesNotExist
from django.db.models.query import Q, QuerySet
from django.template.defaultfilters import capfirst
from django.utils.translation import ugettext_lazy as _
from haystack import connections
from haystack.backends import SQ
from haystack.query import SearchQuerySet
from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag_list

from localtv.models import Video, SiteSettings
from localtv.search_indexes import DATETIME_NULL_PLACEHOLDER


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
    q_class = SQ if isinstance(queryset, SearchQuerySet) else Q
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
    def __init__(self, queryset):
        self.is_haystack = isinstance(queryset, SearchQuerySet)
        if self.is_haystack:
            queryset = queryset.load_all()
        self.queryset = queryset

    def __getitem__(self, k):
        if self.is_haystack:
            results = self.queryset[k]
            if isinstance(results, list):
                return [result.object for result in results
                        if result is not None]
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

    """
    #: The field which will be used in the sort query.
    field = None

    #: A value for which this field will be considered empty and excluded from
    #: the sorted query.
    #:
    #: .. note:: ``None`` will be handled as an ``__isnull`` query, which will
    #:           not be correctly handled by :mod:`haystack`.
    empty_value = EMPTY

    #: A human-readable name for this sort.
    verbose_name = _('Sort')

    def __init__(self, descending=True):
        self.descending = descending

    def get_field(self, queryset):
        """
        Returns the field which will be sorted on. By default, returns the value
        of :attr:`field`.

        """
        return self.field

    def get_empty_value(self, queryset):
        """
        Returns the value for which the queryset's sort field will be considered
        "empty" and excluded from the sorted field. By default, returns
        :attr:`empty_value`.

        """
        return self.empty_value

    def sort(self, queryset):
        """
        Runs the entire sort process; excludes instances which have an empty
        sort field, and does the actual ordering.

        """
        queryset = self.exclude_empty(queryset)
        field = self.get_field(queryset)
        return self.order_by(queryset,
                             ''.join(('-' if self.descending else '', field)))

    def exclude_empty(self, queryset):
        """
        Excludes instances which have an "empty" value in the sort field.

        """
        empty_value = self.get_empty_value(queryset)
        if empty_value is not EMPTY:
            field = self.get_field(queryset)
            q = _q_for_queryset(queryset, field, (empty_value,))
            queryset = queryset.filter(~q)
        return queryset

    def order_by(self, queryset, order_by):
        """Performs the actual ordering for the :class:`Sort`."""
        return queryset.order_by(order_by)


class DummySort(Sort):
    """Looks like a sort, but does nothing."""
    def __init__(self, verbose_name, *args, **kwargs):
        self.verbose_name = verbose_name
        super(DummySort, self).__init__(*args, **kwargs)

    def sort(self, queryset):
        return queryset


class BestDateSort(Sort):
    @property
    def verbose_name(self):
        return _('Newest') if self.descending else _('Oldest')

    def get_field(self, queryset):
        if (isinstance(queryset, SearchQuerySet) and
            SiteSettings.objects.get_current().use_original_date):
            return 'best_date_with_published'
        return 'best_date'

    def sort(self, queryset):
        if not isinstance(queryset, SearchQuerySet):
            queryset = queryset.with_best_date(
                           SiteSettings.objects.get_current().use_original_date)
        return super(BestDateSort, self).sort(queryset)


class NullableDateSort(Sort):
    def get_empty_value(self, queryset):
        if isinstance(queryset, SearchQuerySet):
            return DATETIME_NULL_PLACEHOLDER
        return None


class FeaturedSort(NullableDateSort):
    verbose_name = _('Recently featured')
    field = 'last_featured'


class ApprovedSort(NullableDateSort):
    verbose_name = _('Recently approved')
    field = 'when_approved'


class PopularSort(Sort):
    field = 'watch_count'
    empty_value = 0

    def sort(self, queryset):
        if not isinstance(queryset, SearchQuerySet):
            queryset = queryset.with_watch_count()
        return super(PopularSort, self).sort(queryset)

    def exclude_empty(self, queryset):
        if not isinstance(queryset, SearchQuerySet):
            field = self.get_field(queryset)
            empty_value = self.get_empty_value(queryset)
            return queryset.extra(where=["%s<>%%s" % field],
                                  params=[empty_value])
        return super(PopularSort, self).exclude_empty(queryset)

    def order_by(self, queryset, order_by):
        if not isinstance(queryset, SearchQuerySet):
            return queryset.extra(order_by=[order_by])
        return super(PopularSort, self).order_by(queryset, order_by)
