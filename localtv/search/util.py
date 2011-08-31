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

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from tagging.models import Tag

from localtv.models import Video, Feed, Category
from localtv.playlists.models import Playlist
from localtv.search.forms import SmartSearchForm


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

    #: Defines the available filtering options and the indexes that they
    #: correspond to on the :class:`localtv.search_indexes.VideoIndex`.
    filters = {
        'tag': {'model': Tag, 'fields': ['tags']},
        'category': {'model': Category, 'fields': ['categories']},
        'author': {'model': User, 'fields': ['authors', 'user']},
        'playlist': {'model': Playlist, 'fields': ['playlists']},
        'feed': {'model': Feed, 'fields': ['feed']},
    }
    #: Default filter to use. Should be one of the keys from ``filters``.
    search_filter = None

    def _process_sort(self, sort):
        """
        Parses the sort string and returns a (sort, descending) tuple.

        """
        descending = False
        if sort[0] == '-':
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
            searchqueryset = searchqueryset.order_by(
                            ''.join(('-' if desc else '', order_by)))
        return searchqueryset

    def _filter(self, searchqueryset, search_filter, **kwargs):
        """
        Sets up the searchqueryset to use the specified filter and returns a
        (``searchqueryset``, ``filter_obj``) tuple, where ``filter_obj`` is the
        instance which is being filtered for. If a valid ``search_filter`` is
        provided, but no ``filter_obj`` is found, an Http404 will be raised.

        """
        filter_obj = None
        search_filter = self.filters.get(search_filter, None)
        if search_filter is not None:
            try:
                search_filter['model']._meta.get_field_by_name('site')
            except FieldDoesNotExist:
                pass
            else:
                kwargs['site'] = Site.objects.get_current()

            filter_obj = get_object_or_404(search_filter['model'], **kwargs)
            sq = SQ()
            for field in search_filter['fields']:
                sq |= SQ(**{field: filter_obj.pk})
            searchqueryset = searchqueryset.filter(sq)

        return searchqueryset, filter_obj
