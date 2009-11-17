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

from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.models import Category
from localtv.util import MockQueryset
from localtv.subsite.admin import forms

@require_site_admin
@get_sitelocation
def categories(request, sitelocation=None):
    categories = MockQueryset(Category.in_order(sitelocation.site))
    formset = forms.CategoryFormSet(queryset=categories)

    add_category_form = forms.CategoryForm()
    if request.method == 'GET':
        return render_to_response('localtv/subsite/admin/categories.html',
                                  {'formset': formset,
                                   'add_category_form': add_category_form},
                                  context_instance=RequestContext(request))
    else:
        if request.POST['submit'] == 'Add':
            category = Category(site=sitelocation.site)
            add_category_form = forms.CategoryForm(request.POST, request.FILES,
                                                   instance=category)
            if add_category_form.is_valid():
                try:
                    add_category_form.save()
                except IntegrityError:
                    add_category_form._errors = \
                        'There was an error adding this category.  Does it '\
                        'already exist?'
                else:
                    return HttpResponseRedirect(request.path + '?successful')

            return render_to_response('localtv/subsite/admin/categories.html',
                                      {'formset': formset,
                                       'add_category_form': add_category_form},
                                      context_instance=RequestContext(request))
        elif request.POST['submit'] == 'Save':
            formset = forms.CategoryFormSet(request.POST, request.FILES,
                                            queryset=categories)
            if formset.is_valid():
                formset.save()
                return HttpResponseRedirect(request.path + '?successful')
            else:
                return render_to_response(
                    'localtv/subsite/admin/categories.html',
                    {'formset': formset,
                     'add_category_form': add_category_form},
                    context_instance=RequestContext(request))

        elif request.POST['submit'] == 'Apply':
            formset = forms.CategoryFormSet(request.POST, request.FILES,
                                            queryset=categories)
            if formset.is_valid():
                formset.save()
            action = request.POST['action']
            if action == 'delete':
                for data in  formset.cleaned_data:
                    if data['bulk']:
                        category = data['id']
                        for child in category.child_set.all():
                            # reset children to no parent
                            child.parent = None
                            child.save()
                        data['id'].delete()
            return HttpResponseRedirect(request.path + '?successful')
