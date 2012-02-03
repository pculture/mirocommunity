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

from django import forms
from django.contrib.sites.models import Site
from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import ugettext_lazy as _
from haystack.forms import SearchForm

from localtv.models import Video
from localtv.search.query import SmartSearchQuerySet


class SmartSearchForm(SearchForm):
    def __init__(self, *args, **kwargs):
        sqs = kwargs.get('searchqueryset', None)
        if sqs is None:
            kwargs['searchqueryset'] = SmartSearchQuerySet()
        super(SmartSearchForm, self).__init__(*args, **kwargs)

    def no_query_found(self):
        return self.searchqueryset.all()


class VideoSearchForm(SmartSearchForm):
    def search(self):
        """
        Adjusts the searchqueryset to return only videos associated with the
        current site before performing the search.

        """
        site = Site.objects.get_current()
        self.searchqueryset = self.searchqueryset.models(
                        Video).filter(site=site.pk)
        return super(VideoSearchForm, self).search()


class FilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(FilterForm, self).__init__(*args, **kwargs)
        from localtv.search.utils import SortFilterMixin
        for filter_name, filter_def in SortFilterMixin.filters.iteritems():
            if filter_name not in self.fields:
                model = filter_def['model']
                qs = model._default_manager.all()
                try:
                    model._meta.get_field_by_name('site')
                except FieldDoesNotExist:
                    pass
                else:
                    qs = qs.filter(site=Site.objects.get_current())
                self.fields[filter_name] = forms.ModelMultipleChoiceField(qs,
                            required=False, widget=forms.CheckboxSelectMultiple,
                            label=_(model._meta.verbose_name_plural))
