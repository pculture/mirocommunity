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

from localtv.models import Video, Feed, Category
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


class SortFilterMixin(object):
    """
    Generic mixin to provide standardized haystack-based filtering and sorting
    to any classes that need it.

    """
    form_class = SmartSearchForm
    #: Defines the available sort options and the indexes that they correspond
    #: to on the :class:`localtv.search_indexes.VideoIndex`.
    sorts = {
        'date': 'best_date',
        'featured': 'last_featured',
        'popular': 'watch_count',
        'approved': 'when_approved',

        # deprecated
        'latest': 'best_date'
    }

    #: Defines which items should be excluded when using a given sort. This is a
    #: hack necessitated by lack of __isnull searching in haystack. Max is used
    #: because whoosh can't handle datetime values before 1900. Ick ick ick.
    _empty_value = {
        'featured': datetime.max,
        'approved': datetime.max,
        'popular': 0
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

    def _process_sort(self, sort):
        """
        Parses the sort string and returns a (sort, descending) tuple.

        """
        descending = False
        if sort is not None and sort[0] == '-':
            descending = True
            sort = sort[1:]
        return (sort, descending)

    def _make_search_form(self, query):
        """Creates and returns a search form for the given query."""
        return self.form_class({'q': query})

    def _query(self, query):
        """
        Performs a search for the query and returns an initial SearchQuerySet.

        """
        form = self._make_search_form(query)
        return form.search()

    def _sort(self, searchqueryset, sort):
        """
        Sets up the searchqueryset to use the specified sort and returns it.

        """
        sort, desc = self._process_sort(sort)
        order_by = self.sorts.get(sort, None)
        if order_by is not None:
            if sort in self._empty_value:
                searchqueryset = searchqueryset.exclude(
                                    **{order_by: self._empty_value[sort]})
            searchqueryset = searchqueryset.order_by(
                            ''.join(('-' if desc else '', order_by)))
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
