# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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

import logging

from django import forms
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from haystack.forms import SearchForm

from localtv.models import Video, Category, Feed
from localtv.playlists.models import Playlist
from localtv.search.query import SmartSearchQuerySet
from localtv.search.utils import (BestDateSort, FeaturedSort, ApprovedSort,
                                  PopularSort, TagFilter, ModelFilter,
                                  DummySort)
from localtv.settings import USE_HAYSTACK


class SmartSearchForm(SearchForm):
    def __init__(self, *args, **kwargs):
        sqs = kwargs.get('searchqueryset', None)
        if sqs is None:
            kwargs['searchqueryset'] = SmartSearchQuerySet()
        super(SmartSearchForm, self).__init__(*args, **kwargs)

    def no_query_found(self):
        return self.searchqueryset.all()


class SortFilterFormMetaclass(SmartSearchForm.__metaclass__):
    def __new__(cls, name, bases, attrs):
        new_class = super(VideoFormMetaclass,
                          cls).__new__(cls, name, bases, attrs)
        if 'filters' in attrs:
            for f_name, f in attrs['filters']:
                new_class.base_fields[f_name] = f.formfield()


class SortFilterForm(SmartSearchForm):
    """
    Handles searching, filtering, and sorting for video queries.

    """
    __metaclass__ = SortFilterFormMetaclass

    sorts = SortedDict(
        ('newest', BestDateSort(reversed=True)),
        ('oldest', BestDateSort()),
        ('featured', FeaturedSort()),
        ('popular', PopularSort()),
        ('approved', ApprovedSort()),
        ('relevant', DummySort(_('Relevant')))
    )
    sort = forms.ChoiceField(choices=tuple((k, s.verbose_name)
                                           for k, s in sorts.iteritems()),
                             widget=forms.RadioSelect,
                             required=True,
                             initial='newest')

    filters = {
        'tag': TagFilter(('tags',)),
        'category': ModelFilter(('categories',), Category, 'slug'),
        'author': ModelFilter(('authors', 'user'), User),
        'playlist': ModelFilter(('playlists',), Playlist),
        'feed': ModelFilter(('feed',), Feed)
    }

    def __init__(self, *args, **kwargs):
        """
        Limits the searchqueryset to return only videos associated with the
        current site.

        """
        super(VideoSearchForm, self).__init__(*args, **kwargs)
        self.searchqueryset = self.searchqueryset.filter(
                                                        site=settings.SITE_ID)

    def filter_fields(self):
        """
        Returns a list of fields corresponding to filters.

        """
        return [self[f_name] for f_name in self.fields]

    def search(self):
        """
        Returns a queryset or searchqueryset for the given query, depending
        Adjusts the searchqueryset to return only videos associated with the
        current site before performing the search.

        """
        if USE_HAYSTACK:
            qs = super(VideoSearchForm, self).search()
        else:
            qs = Video.objects.filter(status=Video.ACTIVE,
                                      site=settings.SITE_ID)
            # We can't actually fake a search with the database, so even if
            # USE_HAYSTACK is false, if a search was executed, we try to
            # run a haystack search, then query the database using the pks
            # from the search results. If the database search errors out or
            # returns no results, then an empty queryset will be returned.
            if self.cleaned_data['q']:
                try:
                    results = list(super(VideoSearchForm, self).search())
                except Exception, e:
                    logging.error('Haystack search failed with %s',
                                  e.__class__.__name__,
                                  exc_info=sys.exc_info())
                    results = []

                if results:
                    # We add ordering by pk to preserve the "relevance" sort of
                    # the search. If any other sort is applied, it will override
                    # this.
                    pks = [int(r.pk) for r in results]
                    order = ['-localtv_video.id = %i' % pk for pk in pks]
                    qs = qs.filter(pk__in=pks).extra(order_by=order)
                else:
                    qs = Video.objects.none()
        return qs.filter(site=site.pk)

    def clean(self):
        cleaned_data = self.cleaned_data
        for f_name, f in self.filters.iteritems():
            if f_name in cleaned_data:
                cleaned_data[f_name] = f.clean(cleaned_data[f_name])

        # If there's no search, but relevant is selected for sorting, use the
        # default sort instead.
        if cleaned_data['sort'] == 'relevant' and not cleaned_data['q']:
            cleaned_data['sort'] = self.fields['sort'].initial
        return cleaned_data

    def filter(self, queryset):
        for f_name, f in self.filters.iteritems():
            if f_name in self.cleaned_data:
                queryset = f.filter(queryset, self.cleaned_data[f_name])
        return queryset

    def sort(self, queryset):
        sort = self.sorts[self.cleaned_data['sort']]
        return sort.sort(queryset)
