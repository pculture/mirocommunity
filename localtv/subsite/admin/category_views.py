# Miro Community
# Copyright 2009 - Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.models import Category
from localtv.subsite.admin import forms

@require_site_admin
@get_sitelocation
def categories(request, sitelocation=None):
    categories = Category.in_order(sitelocation.site)
    for category in categories:
        category.form = forms.CategoryForm(prefix="edit_%s" % category.id,
                                           instance=category)
    add_category_form = forms.CategoryForm()
    if request.method == 'GET':
        add_category_form = forms.CategoryForm()
        return render_to_response('localtv/subsite/admin/categories.html',
                                  {'categories': categories,
                                   'add_category_form': add_category_form},
                                  context_instance=RequestContext(request))
    else:
        if request.POST['submit'] == 'Add':
            category = Category(site=sitelocation.site)
            add_category_form = forms.CategoryForm(request.POST,
                                                   instance=category)
            if add_category_form.is_valid():
                try:
                    add_category_form.save()
                except IntegrityError:
                    add_category_form._errors = \
                        'There was an error adding this category.  Does it '\
                        'already exist?'
                else:
                    return HttpResponseRedirect(request.path)

            return render_to_response('localtv/subsite/admin/categories.html',
                                      {'categories': categories,
                                       'add_category_form': add_category_form},
                                      context_instance=RequestContext(request))
        elif request.POST['submit'] == 'Save':
            invalid = False
            for category in categories:
                category.form = forms.CategoryForm(
                    request.POST,
                    request.FILES,
                    prefix="edit_%s" % category.id,
                    instance=category)
                if category.form.is_valid():
                    try:
                        category.form.save()
                    except IntegrityError:
                        category.form._errors = \
                            'There was an error editing %s. Does it already '\
                            'exist?' % category.name
                        invalid = True
                else:
                    invalid = True
            if invalid:
                return render_to_response(
                    'localtv/subsite/admin/categories.html',
                    {'categories': categories,
                     'add_category_form': add_category_form},
                    context_instance=RequestContext(request))
            else:
                return HttpResponseRedirect(request.path)
        elif request.POST['submit'] == 'Apply':
            action = request.POST['action']
            categories = []
            for key in request.POST:
                if key.startswith('bulk_'):
                    id = int(key[5:])
                    categories.append(Category.objects.get(pk=id))
            if action == 'delete':
                for category in categories:
                    category.delete()
            return HttpResponseRedirect(request.path)
