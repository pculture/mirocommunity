# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
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

from datetime import datetime

from django import forms
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models.fields import FieldDoesNotExist
from django.db.models.query import Q, QuerySet
from haystack.backends import SQ
from haystack.query import SearchQuerySet
from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag_list

from localtv.models import Video, Feed, Category, SiteLocation
from localtv.playlists.models import Playlist
from localtv.search.forms import SmartSearchForm, FilterForm
from localtv.search_indexes import DATETIME_NULL_PLACEHOLDER
from localtv.settings import USE_HAYSTACK


EMPTY = object()


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

    """
    #: The field which will be used in the sort query.
    field = None

    #: A value for which this field will be considered empty and excluded from
    #: the sorted query.
    #:
    #: .. note:: ``None`` will be handled as an ``__isnull`` query, which will
    #:           not be correctly handled by :mod:`haystack`.
    empty_value = EMPTY

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

    def sort(self, queryset, descending=False):
        field = self.get_field(queryset)
        empty_value = self.get_empty_value(queryset)
        if empty_value is not EMPTY:
            if empty_value is None:
                kwargs = {'%s__isnull' % field: True}
            else:
                kwargs = {'%s__exact' % field: empty_value}

            queryset = queryset.exclude(**kwargs)
        return queryset.order_by(''.join(('-' if descending else '', field)))


class BestDateSort(Sort):
    def get_field(self, queryset):
        if (isinstance(queryset, SearchQuerySet) and
            SiteLocation.objects.get_current().use_original_date):
            return 'best_date_with_published'
        return 'best_date'

    def sort(self, queryset, descending=False):
        if not isinstance(queryset, SearchQuerySet):
            queryset = queryset.with_best_date(
                           SiteLocation.objects.get_current().use_original_date)
        return super(BestDateSort, self).sort(queryset, descending)


class NullableDateSort(Sort):
    def get_empty_value(self, queryset):
        if isinstance(queryset, SearchQuerySet):
            return DATETIME_NULL_PLACEHOLDER
        return None


class FeaturedSort(NullableDateSort):
    field = 'last_featured'


class ApprovedSort(NullableDateSort):
    field = 'when_approved'


class PopularSort(Sort):
    field = 'watch_count'
    empty_value = 0

    def sort(self, queryset, descending=False):
        if not isinstance(queryset, SearchQuerySet):
            queryset = queryset.with_watch_count()
        return super(PopularSort, self).sort(queryset, descending)


class Filter(object):
    """
    Represents a filter which can be applied to either a :class:`QuerySet` or a
    :class:`SearchQuerySet`.
    """
    #: The field lookups which will be let through the filter if they have a
    #: matching value.
    field_lookups = None

    #: A human-friendly name for the filter, to be used e.g. with
    #: :class:`.FilterForm`.
    verbose_name = None

    def __init__(self, field_lookups):
        self.field_lookups = field_lookups

    def filter(self, queryset, values):
        """
        Returns a queryset filtered to match any of the given ``values`` in
        :attr:`field`.

        """
        q_class = SQ if isinstance(queryset, SearchQuerySet) else Q
        q = None
        for lookup in self.field_lookups:
            if len(values) == 1:
                new_q = q_class(**{"%s__exact" % lookup: values[0]})
            else:
                new_q = q_class(**{"%s__in" % lookup: values})

            if q is None:
                q = new_q
            else:
                q |= new_q
        return queryset.filter(q)

    def clean_filter_values(self, values):
        """
        Given a list of values used to create a filter, returns a list of values
        which are known to be valid and which are in a standard format. This is
        expected to be called on values *before* they are passed to
        :meth:`filter`.

        """
        return values

    def formfield(self, form_class=forms.MultipleChoiceField, **kwargs):
        defaults = {
            'required': False,
            'label': capfirst(self.verbose_name)
        }
        defaults.update(kwargs)
        return form_class(**defaults)


class ModelFilter(Filter):
    #: The model class to be used for cleaning the filter's values.
    model = None

    #: The field on that model which is matched to the values during cleaning.
    field = None

    def __init__(self, field_lookups, model, field='pk'):
        self.model = model
        self.field = field
        super(ModelFilter, self).__init__(field_lookups)

    @property
    def verbose_name(self):
        return self.model._meta.verbose_name_plural

    def filter(self, queryset, values):
        pks = [instance.pk for instance in values]
        return super(ModelFilter, self).filter(queryset, pks)

    def clean_filter_values(self, values):
        if isinstance(values, QuerySet) and values.model == self.model:
            return values._clone()
        elif (isinstance(values, (list, tuple))
              and not any((not isinstance(v, self.model) for v in values))):
            return values
        return self.get_query_set().filter(**{'%s__in' % self.field: values})

    def get_query_set(self):
        qs = self.model._default_manager.all()
        try:
            self.model._meta.get_field_by_name('site')
        except FieldDoesNotExist:
            pass
        else:
            qs = qs.filter(site=Site.objects.get_current())
        return qs

    def formfield(self, form_class=forms.ModelMultipleChoiceField, **kwargs):
        defaults = {
            'widget': forms.CheckboxSelectMultiple,
            'queryset': self.get_query_set()
        }
        defaults.update(kwargs)
        return super(ModelFilter, self).formfield(form_class, **defaults)


class TagFilter(Filter):
    def filter(self, queryset, values):
        if not isinstance(queryset, SearchQuerySet):
            return TaggedItem.objects.with_any(values)
        pks = [instance.pk for instance in values]
        return super(TagFilter, self).filter(queryset, pks)

    def clean_filter_values(self, values):
        return get_tag_list(values)

    def formfield(self, form_class=forms.ModelMultipleChoiceField, **kwargs):
        defaults = {
            'widget': forms.CheckboxSelectMultiple,
            'queryset': Tag.objects.usage_for_queryset(Video.objects.filter(
                            site=Site.objects.get_current(),
                            status=Video.ACTIVE))
        }
        defaults.update(kwargs)
        return super(TagFilter, self).formfield(form_class, **defaults)


class SortFilterMixin(object):
    """
    Generic mixin to provide standardized haystack-based filtering and sorting
    to any classes that need it.

    """
    form_class = SmartSearchForm
    #: Defines the available sort options and the indexes that they correspond
    #: to on the :class:`localtv.search_indexes.VideoIndex`.
    sorts = {
        'date': BestDateSort(),
        'featured': FeaturedSort(),
        'popular': PopularSort(),
        'approved': ApprovedSort(),

        # deprecated
        'latest': BestDateSort()
    }

    #: Defines the available filtering options and the indexes that they
    #: correspond to on the :class:`localtv.search_indexes.VideoIndex`.
    filters = {
        'tag': TagFilter(('tags',)),
        'category': ModelFilter(('categories',), Category, 'slug'),
        'author': ModelFilter(('authors', 'user'), User),
        'playlist': ModelFilter(('playlists',), Playlist),
        'feed': ModelFilter(('feed',), Feed)
    }

    def _process_sort(self, sort_string):
        """
        Parses the sort string and returns a (sort_name, descending) tuple.

        """
        descending = sort_string is not None and sort_string[0] == '-'
        sort_name = sort_string if not descending else sort_string[1:]
        return (sort_name, descending)

    def _make_search_form(self, query):
        """Creates and returns a search form for the given query."""
        return self.form_class({'q': query})

    def _clean_filter_values(self, filters):
        """
        Given a dictionary of (``filter_name``, ``values``) pairs, returns a
        dictionary of (``filter_name``, ``cleaned_values``).

        """
        cleaned_filters = {}
        for filter_name, values in filters.iteritems():
            try:
                f = self.filters[filter_name]
            except KeyError:
                continue
            cleaned_filters[filter_name] = f.clean_filter_values(values)
        return cleaned_filters

    def _search(self, query):
        """
        Performs a search for the query and returns an initial :class:`QuerySet`
        (or :class:`SearchQuerySet`.

        """
        form = self._make_search_form(query)
        return form.search()

    def _sort(self, queryset, sort_string):
        """
        Sets up the queryset to use the sort corresponding to
        ``sort_string`` and returns it. If there is no corresponding sort,
        returns the queryset unmodified.

        """
        sort_name, desc = self._process_sort(sort_string)
        sort = self.sorts.get(sort_name, None)
        if sort is not None:
            return sort.sort(queryset, descending=desc)
        return queryset

    def _filter(self, queryset, cleaned_filters):
        """
        Given a queryset and a dictionary mapping filter_names to cleaned filter
        values, sequentially applies the filters and returns the filtered queryset.

        """
        for filter_name, values in cleaned_filters.iteritems():
            queryset = self.filters[filter_name].filter(queryset, values)
        return queryset


class SortFilterViewMixin(SortFilterMixin):
    """
    Views can define default sorts and filters which can be overridden by GET
    parameters.

    """
    #: Default sort to use. If this is ``None`` (default) or is not found in
    #: :attr:`sorts`, the results will not be ordered.
    default_sort = None

    #: The name of a filter which will be provided as part of the url arguments
    #: rather than as a GET parameter.
    url_filter = None

    #: The kwarg expected from the urlpattern for this view if
    #: :attr:`url_filter` is not ``None``. Default: 'pk'.
    url_filter_kwarg = 'pk'

    #: Form class to use for this view's filtering.
    filter_form_class = FilterForm

    def _get_query(self, request):
        """Fetches the query for the current request."""
        return request.GET.get('q', "")

    def _get_sort(self, request):
        """Fetches the sort for the current request."""
        return request.GET.get('sort', None) or self.default_sort

    def _get_filter_form(self, request):
        """
        Instantiates :attr:`filter_form_class` with the ``GET`` data from the
        request, removes any fields matching :attr:`url_filter`, runs form
        validation, and returns the form.

        """
        filter_form = self.filter_form_class(self, request.GET)
        if self.url_filter is not None:
            filter_form.fields.pop(self.url_filter, None)
        filter_form.is_valid()
        return filter_form

    def _get_filters(self, filter_form, **kwargs):
        """
        Given an instantiated filter form and the url kwargs for the current
        request, returns a dictionary mapping filter names to value lists.

        """
        filters = getattr(filter_form, 'cleaned_data', {}).copy()
        if self.url_filter in self.filters:
            filters[self.url_filter] = [kwargs[self.url_filter_kwarg]]
        return filters
