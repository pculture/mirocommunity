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
from haystack.forms import SearchForm as HaystackForm
from haystack.query import SearchQuerySet
from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag_list

from localtv.models import Video, Category, Feed
from localtv.playlists.models import Playlist
from localtv.search.query import SmartSearchQuerySet
from localtv.search.utils import (BestDateSort, PopularSort, DummySort, Sort,
                                  _q_for_queryset)
from localtv.search_indexes import DATETIME_NULL_PLACEHOLDER
from localtv.settings import USE_HAYSTACK


class FilterMixin(object):
    widget = forms.CheckboxSelectMultiple

    def __init__(self, field_lookups, *args, **kwargs):
        self.field_lookups = field_lookups
        super(FilterMixin, self).__init__(*args, **kwargs)

    def _make_qs(self, queryset, values):
        qs = [_q_for_queryset(queryset, lookup, values)
              for lookup in self.field_lookups]
        return reduce(operator.or_, qs)

    def filter(self, queryset, values):
        """
        Returns a queryset filtered to match any of the given ``values`` in
        :attr:`field`.

        """
        return queryset.filter(self._make_qs(queryset, values))


class DateTimeFilterField(FilterMixin, forms.BooleanField):
    """
    If active, filters out videos that do not have a value for the given
    datetime field lookups.

    """
    def filter(self, queryset, value):
        if not value:
            return queryset
        if isinstance(queryset, SearchQuerySet):
            # See the note in search_indexes on placeholder values.
            value = DATETIME_NULL_PLACEHOLDER
        else:
            value = None
        return queryset.exclude(self._make_qs(queryset, [value]))


class ModelFilterField(FilterMixin, forms.ModelMultipleChoiceField):
    def __init__(self, queryset, field_lookups=None, cache_choices=False,
                 required=False, widget=None, label=None, *args, **kwargs):
        if label is None:
            label = queryset.model._meta.verbose_name_plural
        if hasattr(queryset, 'model'):
            self.model = queryset.model
        super(ModelFilterField, self).__init__(field_lookups, queryset,
                                               cache_choices, required,
                                               widget, label, *args,
                                               **kwargs)

    def clean(self, value):
        if ((isinstance(value, QuerySet) and
             value.model == self.queryset.model) or
            (isinstance(value, (list, tuple)) and
             isinstance(value[0], self.queryset.model))):
            key = self.to_field_name or 'pk'
            value = [getattr(o, key) for o in value]
        return super(ModelFilterField, self).clean(value)

    def filter(self, queryset, values):
        pks = [instance.pk for instance in values]
        return super(ModelFilterField, self).filter(queryset, pks)


class TagFilterField(ModelFilterField):
    def __init__(self, field_lookups=('tags',), cache_choices=False,
                 required=False, widget=None, label=_('Tags'), initial=None,
                 help_text=None, to_field_name='name', *args, **kwargs):
        queryset = Tag.objects.all()
        super(TagFilterField, self).__init__(queryset, field_lookups,
                                             cache_choices, required, widget,
                                             label, initial, help_text,
                                             to_field_name, *args, **kwargs)

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


class SearchForm(HaystackForm):
    """
    Form which provides the basic searching, filtering and sorting options
    for videos.

    """
    sorts = SortedDict((
        ('newest', BestDateSort()),
        ('oldest', BestDateSort(descending=False)),
        ('popular', PopularSort(_('Popularity'))),
        ('featured', Sort(_('Recently featured'), 'last_featured')),
        ('relevant', DummySort(_('Relevance')))
    ))
    sort = forms.ChoiceField(choices=tuple((k, s.verbose_name)
                                           for k, s in sorts.iteritems()),
                             widget=forms.RadioSelect,
                             required=False,
                             initial='relevant')

    tag = TagFilterField()
    category = ModelFilterField(
                            Category.objects.filter(site=settings.SITE_ID),
                            to_field_name='slug',
                            field_lookups=('categories',))
    author = ModelFilterField(
                            User.objects.all(),
                            field_lookups=('authors', 'user'),
                            label=_('Authors'))
    playlist = ModelFilterField(
                            Playlist.objects.filter(site=settings.SITE_ID),
                            field_lookups=('playlists',))
    feed = ModelFilterField(Feed.objects.filter(
                            site=settings.SITE_ID),
                            field_lookups=('feed',))
    featured = DateTimeFilterField(
                            required=False,
                            field_lookups=('last_featured',),
                            label=_('Featured videos'))

    def get_queryset(self, use_haystack=USE_HAYSTACK):
        """Return the base queryset for this form."""
        if use_haystack:
            qs = SmartSearchQuerySet().models(Video)
        else:
            qs = Video.objects.filter(status=Video.ACTIVE)

        return qs.filter(site=settings.SITE_ID)

    def search(self):
        if not self.is_valid():
            return self.invalid_query()

        queryset = self._search()
        queryset = self._filter(queryset)
        queryset = self._sort(queryset)

        if isinstance(queryset, SearchQuerySet) and self.load_all:
            queryset = queryset.load_all()

        return queryset

    def no_query_found(self):
        """
        Returns the queryset for the case where no query string was provided.

        """
        return self.get_queryset()

    def invalid_query(self):
        """
        Returns the queryset for the case where the filters are invalid, or if
        an error occurs connecting to the database.

        """
        return self.get_queryset().none()

    def filter_fields(self):
        """
        Returns a list of fields corresponding to filters.

        """
        return [self[name] for name, field in self.fields.iteritems()
                if isinstance(field, FilterMixin)]

    def clean_sort(self):
        sort = self.cleaned_data['sort']
        if not sort in self.sorts:
            return self.initial.get('sort', self.fields['sort'].initial)
        return sort

    def clean(self):
        cleaned_data = self.cleaned_data
        # 'featured' sort implies the 'featured' filter.
        if cleaned_data.get('sort') == 'featured':
            cleaned_data['featured'] = True

        # If there is no search, use 'newest' in place of 'relevant'.
        if not cleaned_data.get('q') and cleaned_data.get('sort') == 'relevant':
            cleaned_data['sort'] = 'newest'
        return cleaned_data

    def _search(self):
        """
        Handles the basic logic for this form's search process.

        """
        if not self.cleaned_data['q']:
            return self.no_query_found()

        # If a query was made, we always try to use haystack, since the
        # database wouldn't give useful results in this case.
        try:
            results = self.get_queryset(use_haystack=True
                         ).auto_query(self.cleaned_data['q'])
        except Exception, e:
            logging.error('Haystack search failed with %s',
                          e.__class__.__name__,
                          exc_info=sys.exc_info())
            return self.invalid_query()

        if USE_HAYSTACK:
            queryset = results
        else:
            results = list(results)
            if not results:
                queryset = Video.objects.none()
            else:
                # We add ordering by pk to preserve the "relevance" sort
                # of the search. If another sort (such as "newest") is
                # applied later, it will override this.
                pks = [int(r.pk) for r in results]
                order = ['-localtv_video.id = %i' % pk for pk in pks]
                queryset = self.get_queryset().filter(pk__in=pks
                                             ).extra(order_by=order)

        return queryset

    def _filter(self, queryset):
        """Runs each FilterField's filter method on the given queryset."""
        for name, field in self.fields.iteritems():
            if isinstance(field, FilterMixin) and hasattr(self, 'cleaned_data'):
                values = self.cleaned_data[name]
                if values:
                    queryset = field.filter(queryset, values)
        return queryset

    def _sort(self, queryset):
        """Runs the cleaned sort on the given queryset."""
        sort = self.sorts[self.cleaned_data['sort']]
        return sort.sort(queryset)
