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

from django.conf import settings
from django.http import Http404
from django.views.generic import ListView
from django.views.generic.edit import FormMixin

from localtv.search.forms import SortFilterForm


VIDEOS_PER_PAGE = getattr(settings, 'VIDEOS_PER_PAGE', 15)


class SortFilterMixin(FormMixin):
    """
    This mixin provides functionality for pulling sorting and filtering
    choices from GET data, and overriding filters via url kwargs.

    """
    #: The name of a filter which will be provided as part of the url arguments
    #: rather than as a GET parameter.
    url_filter = None

    #: The kwarg expected from the urlpattern for this view if
    #: :attr:`url_filter` is not ``None``. Default: 'pk'.
    url_filter_kwarg = 'pk'

    form_class = SortFilterForm

    def _request_form_data(self, request, **kwargs):
        data = dict(request.GET.iteritems())
        if self.url_filter is not None:
            data[self.url_filter] = [kwargs[self.url_filter_kwarg]]
        return data

    def get_form_kwargs(self):
        return {
            'initial': self.get_initial(),
            'data': self._request_form_data(self.request, **self.kwargs)
        }


class SortFilterView(ListView, SortFilterMixin):
    """
    Generic view for videos; implements pagination, filtering and searching.

    """
    paginate_by = VIDEOS_PER_PAGE
    form_class = SortFilterForm
    context_object_name = 'videos'

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
        return request.GET.get('q', "")

    def get_queryset(self):
        """
        Returns a list based on the results of a haystack search.

        """
        self.form = self.get_form(self.get_form_class())
        self.form.is_valid()
        if (self.url_filter is not None and
            not self.form.cleaned_data.get(self.url_filter)):
            raise Http404
        return self.form.get_queryset()

    def get_context_data(self, **kwargs):
        """
        In addition to the inherited get_context_data methods, populates a
        ``sort_links`` variable in the template context, which contains the
        querystring for the next sort if that option is chosen.

        For example, if the sort is by descending popularity, choosing the
        ``date`` option will sort by descending date, while choosing
        ``popular`` would switch to sorting by ascending popularity.

        """
        context = super(SortFilterView, self).get_context_data(**kwargs)
        context['form'] = self.form
        return context