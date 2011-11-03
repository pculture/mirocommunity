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

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect, Http404
from django.views.generic.base import View, TemplateResponseMixin
from django.views.generic.list import MultipleObjectMixin


class FormSetMixin(object):
    formset_class = None
    initial = {}

    def get_initial(self):
        return self.initial

    def get_formset_class(self):
        return self.formset_class

    def get_formset_kwargs(self):
        kwargs = {
            'initial': self.get_initial()
        }
        if self.request.method == 'POST':
            kwargs['data'] = self.request.POST
        return kwargs

    def get_formset(self, formset_class):
        return formset_class(**self.get_formset_kwargs())

    def get_context_data(self, **kwargs):
        return kwargs

    def get_success_url(self):
        if self.success_url:
            url = self.success_url
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def formset_valid(self, formset):
        return HttpResponseRedirect(self.get_success_url())

    def formset_invalid(self, formset):
        return self.render_to_response(self.get_context_data(formset=formset))


class ModelFormSetMixin(FormSetMixin, MultipleObjectMixin):
    def get_formset_kwargs(self):
        kwargs = super(ModelFormSetMixin, self).get_formset_kwargs()
        kwargs.update({
            'queryset': self.object_list
        })
        return kwargs

    def formset_valid(self, formset):
        self.object_list = formset.save()
        return super(ModelFormSetMixin, self).formset_valid()

    def get_context_data(self, **kwargs):
        return MultipleObjectMixin.get_context_data(self, **kwargs)



class ProcessFormSetView(View):
    def get(self, request, *args, **kwargs):
        formset_class = self.get_formset_class()
        formset = self.get_formset(formset_class)
        return self.render_to_response(self.get_context_data(formset=formset))
    
    def post(self, request, *args, **kwargs):
        formset_class = self.get_formset_class()
        formset = self.get_formset(formset_class)
        if formset.is_valid():
            return self.formset_valid(formset)
        else:
            return self.formset_invalid(formset)


class BulkEditView(TemplateResponseMixin, ModelFormSetMixin, ProcessFormSetView):
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()
        if not allow_empty and len(self.object_list) == 0:
            raise Http404
        return super(BulkEditView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()
        if not allow_empty and len(self.object_list) == 0:
            raise Http404
        return super(BulkEditView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs['object_list'] = self.object_list
        return super(BulkEditView, self).get_context_data(**kwargs)
