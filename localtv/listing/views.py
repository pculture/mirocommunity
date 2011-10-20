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

import datetime

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, Page
from django.http import Http404
from django.views.generic import ListView
from django.conf import settings
from haystack.query import SearchQuerySet

import localtv.settings
from localtv.models import Video, Category
from localtv.search.forms import VideoSearchForm
from localtv.search.utils import (SortFilterViewMixin, NormalizedVideoList,
                                  ApprovedSort)
from localtv.search_indexes import DATETIME_NULL_PLACEHOLDER


VIDEOS_PER_PAGE = getattr(settings, 'VIDEOS_PER_PAGE', 15)
MAX_VOTES_PER_CATEGORY = getattr(settings, 'MAX_VOTES_PER_CATEGORY', 3)


class VideoSearchView(ListView, SortFilterViewMixin):
    """
    Generic view for videos; implements pagination, filtering and searching.

    """
    paginate_by = VIDEOS_PER_PAGE
    form_class = VideoSearchForm
    context_object_name = 'video_list'

    #: Period of time within which the video was approved.
    approved_since = None

    def get_paginate_by(self, queryset):
        paginate_by = self.request.GET.get('count')
        if paginate_by:
            try:
                paginate_by = int(paginate_by)
            except ValueError:
                paginate_by = None
        if paginate_by is None:
            paginate_by = self.paginate_by
        return paginate_by

    def _get_query(self, request):
        """Fetches the query for the current request."""
        # Support old-style templates that used "query". Remove in 2.0.
        key = 'q' if 'q' in request.GET else 'query'
        return request.GET.get(key, "")

    def get_queryset(self):
        """
        Returns a list based on the results of a haystack search.

        """
        qs = self._search(self._get_query(self.request))
        qs = self._sort(qs, self._get_sort(self.request))

        self.filter_form = self._get_filter_form(self.request)
        filters = self._get_filters(self.filter_form, **self.kwargs)
        self._cleaned_filters = self._clean_filter_values(filters)
        qs = self._filter(qs, self._cleaned_filters)

        if self.approved_since is not None:
            if isinstance(qs, SearchQuerySet):
                qs = qs.exclude(when_approved__exact=DATETIME_NULL_PLACEHOLDER)
            else:
                qs = qs.exclude(when_approved__isnull=True)
            qs = qs.filter(when_approved__gt=(
                                datetime.datetime.now() - self.approved_since))

        return NormalizedVideoList(qs)

    def get_context_data(self, **kwargs):
        """
        In addition to the inherited get_context_data methods, populates a
        ``sort_links`` variable in the template context, which contains the
        querystring for the next sort if that option is chosen.

        For example, if the sort is by descending popularity, choosing the
        ``date`` option will sort by descending date, while choosing
        ``popular`` would switch to sorting by ascending popularity.

        """
        context = ListView.get_context_data(self, **kwargs)
        form = self._make_search_form(self._get_query(self.request))
        context['form'] = form
        form.is_valid()
        context['query'] = form.cleaned_data['q']

        sort, desc = self._process_sort(self._get_sort(self.request))
        sort_links = {}

        for s in self.sorts:
            querydict = self.request.GET.copy()
            querydict.pop('sort', None)
            querydict.pop('page', None)
            if s == sort:
                # Reverse the current ordering if the sort is active.
                querydict['sort'] = ''.join(('' if desc else '-', s))
            else:
                # Default to descending.
                querydict['sort'] = ''.join(('-', s))
            sort_links[s] = ''.join(('?', querydict.urlencode()))
        context['sort_links'] = sort_links

        context['filters'] = self._cleaned_filters
        context['filter_form'] = self.filter_form
        if self.url_filter in self._cleaned_filters:
            try:
                context[self.url_filter] = (
                    self._cleaned_filters[self.url_filter][0])
            except IndexError:
                # Then there are no items matching the url_filter - so we're
                # on a page that shouldn't exist.
                raise Http404

        return context


class SiteListView(ListView):
    """
    Filters the ordinary queryset according to the current site.
    
    """
    def get_queryset(self):
        return super(SiteListView, self).get_queryset().filter(
                                site=Site.objects.get_current())
