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

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models.fields import FieldDoesNotExist
from haystack.backends import SQ
from tagging.models import Tag

from localtv.models import Video, Feed, Category, SiteLocation
from localtv.playlists.models import Playlist
from localtv.search.forms import SmartSearchForm, FilterForm


class SearchQuerysetSliceHack(object):
    """
    Wraps a haystack SearchQueryset so that slice operations and __getitem__
    calls return :class:`localtv.models.Video` instances efficiently instead of
    returning result objects. This is a hack for backwards compatibility.

    """
    def __init__(self, searchqueryset):
        self.searchqueryset = searchqueryset

    def __getitem__(self, k):
        results = self.searchqueryset[k]
        if isinstance(results, list):
            return [result.object for result in results
                    if result is not None]
        return result.object

    def __len__(self):
        return len(self.searchqueryset)

    def __iter__(self):
        return iter(self.searchqueryset)


class Sort(object):
    """
    Class representing a sort which can be performed on a
    :class:`SearchQuerySet` and the methods which make that sort work.

    """
    #: The index which will be used in the sort query.
    sort_index = None

    #: If not ``None``, a value which is used as a filler for being 'empty'.
    #: This is an unfortunate hack necessitated by lack of ``__isnull``
    #: searching in :mod:`haystack`.
    #:
    #: .. note:: Datetime indexes using this hack should use ``datetime.max``
    #:           rather than ``datetime.min`` because :mod:`whoosh` doesn't
    #:           support datetime values before 1900.
    empty_value = None

    def sort(self, queryset, descending=False):
        if self.empty_value is not None:
            queryset = queryset.exclude(**{
                        '%s__exact' % self.sort_field: self.empty_value})
        return queryset.order_by(''.join(('-' if descending else '',
                                          self.sort_field)))


class BestDateSort(Sort):
    @property
    def sort_field(self):
        if SiteLocation.objects.get_current().use_original_date:
            return 'best_date_with_published'
        return 'best_date'


class FeaturedSort(Sort):
    sort_field = 'last_featured'
    empty_value = datetime.max


class ApprovedSort(Sort):
    sort_field = 'when_approved'
    empty_value = datetime.max

class PopularSort(Sort):
    sort_field = 'watch_count'
    empty_value = 0


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
        'tag': {'model': Tag, 'fields': ['tags']},
        'category': {'model': Category, 'fields': ['categories']},
        'author': {'model': User, 'fields': ['authors', 'user']},
        'playlist': {'model': Playlist, 'fields': ['playlists']},
        'feed': {'model': Feed, 'fields': ['feed']},
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

    def _query(self, query):
        """
        Performs a search for the query and returns an initial SearchQuerySet.

        """
        form = self._make_search_form(query)
        return form.search()

    def _sort(self, searchqueryset, sort_string):
        """
        Sets up the searchqueryset to use the sort corresponding to
        ``sort_string`` and returns it. If there is no corresponding sort,
        returns the searchqueryset unmodified.

        """
        sort_name, desc = self._process_sort(sort_string)
        sort = self.sorts.get(sort_name, None)
        if sort is not None:
            return sort.sort(searchqueryset, descending=desc)
        return searchqueryset

    def _get_filter_objects(self, model_class, **kwargs):
        try:
            model_class._meta.get_field_by_name('site')
        except FieldDoesNotExist:
            pass
        else:
            kwargs['site'] = Site.objects.get_current()
        return model_class._default_manager.filter(**kwargs)

    def _filter(self, searchqueryset, **kwargs):
        """
        Sets up the searchqueryset to use the specified filter(s) and returns a
        (``searchqueryset``, ``clean_filter_dict``) tuple, where
        ``clean_filter_dict`` is a dictionary mapping valid filter names to
        iterables of model instances which are being filtered for.

        Any ``kwargs`` which are valid filter names are expected to be either an
        iterable of filter objects or dictionaries to be passed as ``kwargs``
        to :meth:`_get_filter_objects`.

        """
        clean_filter_dict = {}
        for filter_name, filter_objects in kwargs.iteritems():
            filter_def = self.filters.get(filter_name, None)
            if filter_def is not None:
                if isinstance(filter_objects, dict):
                    new_filter_objects = self._get_filter_objects(
                            filter_def['model'], **filter_objects)
                else:
                    try:
                        new_filter_objects = list(filter_objects)
                    except TypeError:
                        new_filter_objects = []
                clean_filter_dict[filter_name] = new_filter_objects
                if new_filter_objects:
                    pks = [obj.pk for obj in new_filter_objects]
                    sq = None

                    for field in filter_def['fields']:
                        if len(pks) > 1:
                            # Use __in if there are multiple pks.
                            new_sq = SQ(**{"%s__in" % field: pks})
                        else:
                            # Otherwise do an exact query on the single pk.
                            new_sq = SQ(**{field: pks[0]})
                        if sq is None:
                            sq = new_sq
                        else:
                            sq |= new_sq
                    searchqueryset = searchqueryset.filter(sq)
        return searchqueryset, clean_filter_dict


class SortFilterViewMixin(SortFilterMixin):
    """
    Views can define default sorts and filters which can be overridden by GET
    parameters.

    """
    default_sort = None
    default_filter = None
    filter_form_class = FilterForm

    def _get_query(self, request):
        """Fetches the query for the current request."""
        return request.GET.get('q', "")

    def _get_sort(self, request):
        """Fetches the sort for the current request."""
        return request.GET.get('sort', self.default_sort)

    def _get_filter_info(self, request, default=None):
        """
        Returns a ``(filter_dict, filter_form)`` tuple. ``filter_form`` is used
        to clean the raw request data. ``filter_dict`` is a dictionary suitable
        for passing to :meth:`._filter`. It is equivalent to
        ``filter_form.cleaned_data``, except that if a ``default`` is provided
        and :attr:`.default_filter` is not ``None``, that value will override
        any values that may have been passed with the request for that filter.

        """
        filter_form = self.filter_form_class(request.GET)
        filter_form.is_valid()
        filter_dict = getattr(filter_form, 'cleaned_data', {}).copy()

        if default is not None and self.default_filter is not None:
            filter_dict[self.default_filter] = default

        return filter_dict, filter_form
