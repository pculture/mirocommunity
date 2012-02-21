# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
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
    """
    Form for filtering the results of a GET request for a filtered view. Takes
    the view instance as an additional first argument on ``__init__``.

    """
    def __init__(self, view, *args, **kwargs):
        super(FilterForm, self).__init__(*args, **kwargs)
        for filter_name, f in view.filters.iteritems():
            if filter_name not in view.filters:
                self.fields[filter_name] = f.formfield()
