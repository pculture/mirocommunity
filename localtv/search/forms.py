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
import operator
import sys

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from django.utils.functional import SimpleLazyObject
from haystack.forms import SearchForm
from haystack.query import SearchQuerySet
from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag_list

from localtv.models import Video, Category, Feed
from localtv.playlists.models import Playlist
from localtv.search.query import SmartSearchQuerySet
from localtv.search.utils import (BestDateSort, FeaturedSort, ApprovedSort,
                                  PopularSort, DummySort, _q_for_queryset)
from localtv.settings import USE_HAYSTACK


class SmartSearchForm(SearchForm):
    def __init__(self, *args, **kwargs):
        sqs = kwargs.get('searchqueryset', None)
        if sqs is None:
            kwargs['searchqueryset'] = SmartSearchQuerySet()
        super(SmartSearchForm, self).__init__(*args, **kwargs)

    def no_query_found(self):
        return self.searchqueryset.all()


class FilterField(forms.ModelMultipleChoiceField):
    widget = forms.CheckboxSelectMultiple

    def __init__(self, queryset, cache_choices=False, required=False, *args,
                 **kwargs):
        super(FilterField, self).__init__(queryset, cache_choices, required,
                                          *args, **kwargs)

    def filter(self, queryset, values):
        """
        Returns a queryset filtered to match any of the given ``values`` in
        :attr:`field`.

        """
        pks = [instance.pk for instance in values]
        qs = [_q_for_queryset(queryset, lookup, pks)
              for lookup in self.field_lookups]
        return queryset.filter(reduce(operator.or_, qs))


class ModelFilterField(FilterField):
    def __init__(self, queryset, field_lookups=None, cache_choices=False,
                 required=False, widget=None, label=None, *args, **kwargs):
        self.field_lookups = field_lookups
        if label is None:
            label = queryset.model._meta.verbose_name_plural
        super(ModelFilterField, self).__init__(queryset, cache_choices,
                                               required, widget, label, *args,
                                               **kwargs)

    def clean(self, value):
        if (isinstance(value, QuerySet) or
            (isinstance(value, (list, tuple)) and
             isinstance(value[0], self.queryset.model))):
            key = self.to_field_name or 'pk'
            value = [getattr(o, key) for o in value]
        return super(ModelFilterField, self).clean(value)


class TagFilterField(ModelFilterField):
    def __init__(self, *args, **kwargs):
        queryset = SimpleLazyObject(lambda: Tag.objects.usage_for_queryset(
                                                Video.objects.filter(
                                                    site=settings.SITE_ID,
                                                    status=Video.ACTIVE)))
        super(TagFilterField, self).__init__(queryset, *args, **kwargs)

    def clean(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])
        elif not self.required and not value:
            return []
        try:
            return get_tag_list(value)
        except ValueError:
            raise ValidationError(self.error_messages['list'])

    def filter(self, queryset, values):
        if not isinstance(queryset, SearchQuerySet):
            return TaggedItem.objects.get_union_by_model(queryset, values)
        return super(TagFilterField, self).filter(queryset, values)


class SortFilterForm(SmartSearchForm):
    """
    Handles searching, filtering, and sorting for video queries.

    """
    sorts = SortedDict((
        ('newest', BestDateSort()),
        ('oldest', BestDateSort(descending=False)),
        ('featured', FeaturedSort()),
        ('popular', PopularSort()),
        ('approved', ApprovedSort()),
        ('relevant', DummySort(_('Relevant')))
    ))
    sort = forms.ChoiceField(choices=tuple((k, s.verbose_name)
                                           for k, s in sorts.iteritems()),
                             widget=forms.RadioSelect,
                             required=False,
                             initial='newest')

    tag = TagFilterField(label=_('Tags'), field_lookups=('tags',))
    category = ModelFilterField(Category.objects.filter(
                                                    site=settings.SITE_ID),
                                to_field_name='slug',
                                field_lookups=('categories',))
    author = ModelFilterField(User.objects.all(), field_lookups=('authors',
                                                                 'user'),
                              label=_('Authors'))
    playlist = ModelFilterField(Playlist.objects.filter(
                                                    site=settings.SITE_ID),
                                field_lookups=('playlists',))
    feed = ModelFilterField(Feed.objects.filter(site=settings.SITE_ID),
                            field_lookups=('feed',))

    def __init__(self, *args, **kwargs):
        """
        Limits the searchqueryset to return only videos associated with the
        current site.

        """
        super(SortFilterForm, self).__init__(*args, **kwargs)
        self.searchqueryset = self.searchqueryset.filter(
                                                        site=settings.SITE_ID)

    def filter_fields(self):
        """
        Returns a list of fields corresponding to filters.

        """
        return [self[name] for name, field in self.fields
                if isinstance(field, FilterField)]

    def clean(self):
        cleaned_data = self.cleaned_data
        # If there is a search, and no explicit sort was selected, sort by
        # relevance.
        if cleaned_data.get('q') and not cleaned_data.get('sort'):
            cleaned_data['sort'] = 'relevant'
        # If there's no search, but relevant is selected for sorting, use the
        # default sort instead.
        if (not cleaned_data.get('q') and
            cleaned_data.get('sort') == 'relevant'):
            cleaned_data.pop('sort')
        return cleaned_data

    def _search(self):
        """
        Returns a queryset or searchqueryset for the given query, depending
        Adjusts the searchqueryset to return only videos associated with the
        current site before performing the search.

        """
        if USE_HAYSTACK:
            qs = super(SortFilterForm, self).search()
        else:
            # We can't actually fake a search with the database, so even if
            # USE_HAYSTACK is false, if a search was executed, we try to
            # run a haystack search, then query the database using the pks
            # from the search results. If the database search errors out or
            # returns no results, then an empty queryset will be returned.
            if self.cleaned_data['q']:
                try:
                    results = list(super(SortFilterForm, self).search())
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
                    qs = Video.objects.filter(pk__in=pks
                                     ).extra(order_by=order)
                else:
                    qs = Video.objects.none()
            else:
                qs = Video.objects.filter(status=Video.ACTIVE,
                                          site=settings.SITE_ID)
        return qs

    def _filter(self, queryset):
        for name, field in self.fields.iteritems():
            if isinstance(field, FilterField) and hasattr(self, 'cleaned_data'):
                values = self.cleaned_data[name]
                if values:
                    queryset = field.filter(queryset, values)
        return queryset

    def _sort(self, queryset):
        try:
            sort = self.sorts[self.cleaned_data['sort']]
        except KeyError:
            sort = self.sorts[self.fields['sort'].initial]
        return sort.sort(queryset)

    def get_queryset(self):
        """
        Searches, filters, and sorts based on the form's cleaned_data.

        """
        queryset = self._search()
        queryset = self._filter(queryset)
        return self._sort(queryset)
