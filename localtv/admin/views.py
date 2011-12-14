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
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.forms.formsets import BaseFormSet, formset_factory
from django.forms.models import (ModelForm, BaseModelFormSet,
                                 modelformset_factory)
from django.http import HttpResponseRedirect, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.generic.base import View, RedirectView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import (MultipleObjectMixin,
                                       MultipleObjectTemplateResponseMixin)

from localtv.decorators import require_site_admin


class FormSetMixin(object):
    factory_function = staticmethod(formset_factory)
    formset_class = BaseFormSet
    form_class = None
    initial = {}
    factory_kwargs = {
        'extra': 0,
        'can_delete': True,
        'max_num': 0,
    }

    def get_initial(self):
        return self.initial

    def get_factory_kwargs(self):
        kwargs = self.factory_kwargs.copy()
        kwargs.update({
            'form': self.form_class,
            'formset': self.formset_class,
        })
        return kwargs

    def get_form_class(self):
        return self.form_class

    def get_formset_class(self):
        return self.factory_function(**self.get_factory_kwargs())

    def get_formset_kwargs(self):
        kwargs = {
            'initial': self.get_initial()
        }
        if self.request.method == 'POST':
            kwargs['data'] = self.request.POST
        return kwargs

    def get_formset(self, formset_class, **kwargs):
        return formset_class(**self.get_formset_kwargs(**kwargs))

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
    factory_function = staticmethod(modelformset_factory)
    formset_class = BaseModelFormSet
    form_class = ModelForm

    def get_queryset(self):
        qs = super(ModelFormSetMixin, self).get_queryset()
        # Force ordering on the queryset here so that it isn't tried by the
        # formset later.
        if not qs.ordered:
            qs = qs.order_by(qs.model._meta.pk.name)
        return qs

    def get_factory_kwargs(self):
        if self.model is not None:
            model = self.model
        elif self.object_list is not None:
            model = self.object_list.model
        else:
            raise ImproperlyConfigured

        kwargs = super(ModelFormSetMixin, self).get_factory_kwargs()
        kwargs['model'] = model
        return kwargs

    def get_formset_kwargs(self, queryset=None):
        kwargs = super(ModelFormSetMixin, self).get_formset_kwargs()
        kwargs.update({
            'queryset': queryset or self.object_list
        })
        return kwargs

    def formset_valid(self, formset):
        self.object_list = formset.save()
        return super(ModelFormSetMixin, self).formset_valid(formset)

    def get_context_data(self, **kwargs):
        return MultipleObjectMixin.get_context_data(self, **kwargs)


class ModelFormSetView(MultipleObjectTemplateResponseMixin, ModelFormSetMixin, View):
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()
        if not allow_empty and len(self.object_list) == 0:
            raise Http404

        context = self.get_context_data(object_list=self.object_list)
        queryset = context['object_list']
        formset_class = self.get_formset_class()
        formset = self.get_formset(formset_class, queryset=queryset)
        context['formset'] = formset
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()
        if not allow_empty and len(self.object_list) == 0:
            raise Http404

        context = self.get_context_data(object_list=self.object_list)
        queryset = context['object_list']
        formset_class = self.get_formset_class()
        formset = self.get_formset(formset_class, queryset=queryset)
        if formset.is_valid():
            return self.formset_valid(formset)
        else:
            return self.formset_invalid(formset, context)

    def formset_invalid(self, formset, context):
        context['formset'] = formset
        return self.render_to_response(context)


class MiroCommunityAdminCRUDMixin(object):
    list_view_name = None
    create_view_name = None
    update_view_name = None
    delete_view_name = None

    @method_decorator(require_site_admin)
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return View.dispatch(self, request, *args, **kwargs)

    def get_template_names(self):
        if isinstance(self.template_name, basestring):
            return [self.template_name]
        else:
            return list(self.template_name)

    def get_success_url(self):
        return reverse(self.list_view_name)

    def get_context_data(self, **kwargs):
        if hasattr(self, 'model') and self.model is not None:
            model = self.model
        elif hasattr(self, 'object') and self.object is not None:
            model = self.object.__class__
        else:
            model = self.get_queryset().model
        return {
            'verbose_name': model._meta.verbose_name,
            'verbose_name_plural': model._meta.verbose_name_plural,
            'list_view_name': self.list_view_name,
            'create_view_name': self.create_view_name,
            'update_view_name': self.update_view_name,
            'delete_view_name': self.delete_view_name,
        }


class MiroCommunityAdminListView(MiroCommunityAdminCRUDMixin, ModelFormSetView):
    def get_context_data(self, **kwargs):
        context = ModelFormSetView.get_context_data(self, **kwargs)
        context.update(
            MiroCommunityAdminCRUDMixin.get_context_data(self, **kwargs)
        )
        return context

    def get_success_url(self):
        return self.request.path


class MiroCommunityAdminCreateView(MiroCommunityAdminCRUDMixin, CreateView):
    def get_context_data(self, **kwargs):
        context = CreateView.get_context_data(self, **kwargs)
        context.update(
            MiroCommunityAdminCRUDMixin.get_context_data(self, **kwargs)
        )
        return context


class MiroCommunityAdminUpdateView(MiroCommunityAdminCRUDMixin, UpdateView):
    def get_context_data(self, **kwargs):
        context = UpdateView.get_context_data(self, **kwargs)
        context.update(
            MiroCommunityAdminCRUDMixin.get_context_data(self, **kwargs)
        )
        return context


class MiroCommunityAdminDeleteView(MiroCommunityAdminCRUDMixin, DeleteView):
    def get_context_data(self, **kwargs):
        context = DeleteView.get_context_data(self, **kwargs)
        context.update(
            MiroCommunityAdminCRUDMixin.get_context_data(self, **kwargs)
        )
        return context


class ViewNameRedirectView(RedirectView):
    """
    A RedirectView which can reverse a view's name.

    """
    view_name = None
    def get_redirect_url(self, **kwargs):
        if self.view_name is not None:
            return reverse(self.view_name, kwargs=kwargs)
        else:
            return super(ViewNameRedirectView, self).get_redirect_url(**kwargs)
