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

import datetime

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, Page
from django.http import Http404
from django.views.generic import ListView
from django.conf import settings
from voting.models import Vote

import localtv.settings
from localtv.models import Video, Category
from localtv.search.forms import VideoSearchForm
from localtv.search.utils import SortFilterViewMixin, SearchQuerysetSliceHack


VIDEOS_PER_PAGE = getattr(settings, 'VIDEOS_PER_PAGE', 15)
MAX_VOTES_PER_CATEGORY = getattr(settings, 'MAX_VOTES_PER_CATEGORY', 3)


class VideoSearchView(ListView, SortFilterViewMixin):
    """
    Generic view for videos; implements pagination, filtering and searching.

    """
    paginate_by = VIDEOS_PER_PAGE
    form_class = VideoSearchForm
    context_object_name = 'video_list'

    #: Default sort method to use. Should be one of the keys from ``sorts``.
    default_sort = None

    #: Default filter to use. Should be one of the keys from ``filters``.
    default_filter = None

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
        sqs = self._query(self._get_query(self.request))
        sqs = self._sort(sqs, self._get_sort(self.request))
        filter_dict, self.filter_form = self._get_filter_info(self.request,
                                                              self.kwargs)
        sqs, self._filter_dict = self._filter(sqs, **filter_dict)
        if self.approved_since is not None:
            sqs = sqs.exclude(
                when_approved=self._empty_value['approved']
            ).filter(when_approved__gt=(
                            datetime.datetime.now() - self.approved_since))

        # :meth:`SearchQuerySet.load_all` sets the queryset up to load all, but
        # doesn't actually perform any loading; this will only happen when the
        # cache is filled.
        return SearchQuerysetSliceHack(sqs.load_all())

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

        context['filters'] = self._filter_dict
        context['filter_form'] = self.filter_form
        if self.default_filter in self._filter_dict:
            context[self.default_filter] = (
                self._filter_dict[self.default_filter][0])

        return context


class SiteListView(ListView):
    """
    Filters the ordinary queryset according to the current site.
    
    """
    def get_queryset(self):
        return super(SiteListView, self).get_queryset().filter(
                                site=Site.objects.get_current())


class CategoryVideoSearchView(VideoSearchView):
    """
    Adds support for voting on categories. Essentially, all this means is that
    a ``user_can_vote`` variable is added to the context.

    """
    def get_context_data(self, **kwargs):
        context = VideoSearchView.get_context_data(self, **kwargs)
        category = context['category']

        user_can_vote = False
        if (localtv.settings.voting_enabled() and 
                    category.contest_mode and
                    request.user.is_authenticated()):
            # TODO: Benchmark this against a version where the pk queryset is
            # evaluated here instead of becoming a subquery.
            pks = category.approved_set().filter(
                site=Site.objects.get_current()).values_list('id', flat=True)
            user_can_vote = True
            votes = Vote.objects.filter(
                    content_type=ContentType.objects.get_for_model(Video),
                    object_id__in=pks,
                    user=self.request.user).count()
            if votes >= MAX_VOTES_PER_CATEGORY:
                user_can_vote = False
        context['user_can_vote'] = user_can_vote
        return context
