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
        data = request.GET.dict()
        if self.url_filter is not None:
            data[self.url_filter] = [kwargs[self.url_filter_kwarg]]
        # If the sort is provided in the kwargs, enforce it.
        if 'sort' in kwargs:
            data['sort'] = kwargs['sort']
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

    def get_queryset(self):
        """
        Returns the results of :attr:`form_class`\ 's ``get_queryset()``
        method.

        """
        form = self.form = self.get_form(self.get_form_class())

        if form.is_valid():
            return form.get_queryset()
        else:
            if self.url_filter in form.errors:
                raise Http404
            return form.no_query_found()

    def get_context_data(self, **kwargs):
        context = super(SortFilterView, self).get_context_data(**kwargs)
        context['form'] = self.form
        return context