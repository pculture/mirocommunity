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

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db.models.fields import FieldDoesNotExist
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.views.generic.edit import FormMixin
from django.conf import settings
from haystack.backends import SQ
from tagging.models import Tag
from voting.models import Vote

import localtv.settings
from localtv.models import Video, Feed, Category
from localtv.playlists.models import Playlist
from localtv.search.forms import VideoSearchForm
from localtv.search.query import SmartSearchQuerySet


VIDEOS_PER_PAGE = getattr(settings, 'VIDEOS_PER_PAGE', 15)
MAX_VOTES_PER_CATEGORY = getattr(settings, 'MAX_VOTES_PER_CATEGORY', 3)


class VideoSearchView(ListView, FormMixin):
    """
    Generic view for videos; implements pagination, filtering and searching.

    """
    paginate_by = VIDEOS_PER_PAGE
    form_class = VideoSearchForm
    context_object_name = 'video_list'
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
    #: Default sort method to use. Should be one of the keys from ``sorts``.
    default_sort = None

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

    def get_form_kwargs(self):
        kwargs = super(VideoSearchView, self).get_form_kwargs()
        data = self.request.GET.copy()

        # HACK to support old custom templates
        # XXX: How old? Perhaps remove in 2.0.
        if 'q' not in data and 'query' in data:
            data['q'] = data['query']

        kwargs['data'] = data
        return kwargs

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        self._search_form = self.get_form(form_class)
        self._searchqueryset = self._search_form.search()
        return super(VideoSearchView, self).get(request, *args, **kwargs)

    def _get_sort(self):
        if not hasattr(self, '_sort'):
            self._sort = self.request.GET.get('sort', self.default_sort)
            if self._sort:
                self._sort_desc = False
                if self._sort[0] == '-':
                    self._sort_desc = True
                    self._sort = self._sort[1:]
        return self._sort

    def get_searchqueryset(self):
        """
        Performs a haystack search and sort using
        :class:`~localtv.search.forms.VideoSearchForm`. Three sort options are
        currently supported: ``date``, ``featured``, and ``popular``.

        """
        current_site = Site.objects.get_current()
        # self._searchqueryset is set during form validation handling.
        sqs = self._searchqueryset

        sort = self._get_sort()
        order_by = self.sorts.get(sort, None)

        if order_by is not None:
            sqs = sqs.order_by(
                ''.join(('-' if self._sort_desc else '', order_by))
            )

        if self.approved_since is not None:
            sqs = sqs.filter(when_approved__gt=(
                        datetime.datetime.now() - self.approved_since))

        if self.default_filter in self.filters:
            search_filter = self.filters[self.default_filter]
            filter_obj_kwargs = self.kwargs.copy()

            try:
                search_filter['model']._meta.get_field_by_name('site')
            except FieldDoesNotExist:
                pass
            else:
                filter_obj_kwargs['site'] = Site.objects.get_current()

            self._filter_obj = get_object_or_404(
                        search_filter['model'], **filter_obj_kwargs)
            sq = SQ()
            for field in search_filter['fields']:
                sq |= SQ(**{field: self._filter_obj})
            sqs = sqs.filter(sq)

        return sqs

    def get_queryset(self):
        """
        Returns a MockQuerySet based on the results of a haystack search.

        """
        sqs = self.get_searchqueryset()
        sqs.load_all()
        
        # For now, make it a simple list. Might need to support some
        # queryset methods later.
        return [result.object for result in sqs]

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
        context['form'] = self._search_form

        cleaned_data = getattr(context['form'], 'cleaned_data', {})
        context['query'] = cleaned_data.get('q', '')

        sort = self._get_sort()
        sort_links = {}

        for s in self.sorts:
            querydict = self.request.GET.copy()
            querydict.pop('sort', None)
            querydict.pop('page', None)
            if s == sort:
                # Reverse the current ordering if the sort is active.
                querydict['sort'] = ''.join(('' if self._sort_desc else '-', s))
            else:
                # Default to descending.
                querydict['sort'] = ''.join(('-', s))
            sort_links[s] = ''.join(('?', querydict.urlencode()))
        context['sort_links'] = sort_links

        if self.default_filter in self.filters:
            # Then by now, self._filter_obj is either populated or a 404
            # has been raised.
            context[self.default_filter] = self._filter_obj

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
            pks = Category.approved_set().filter(
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
