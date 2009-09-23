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
            formset = forms.CategoryFormSet(request.POST, request.FILES,
                                            queryset=categories)
            if formset.is_valid():
                formset.save()
                return HttpResponseRedirect(request.path)
            else:
                return render_to_response(
                    'localtv/subsite/admin/categories.html',
                    {'categories': categories,
                     'add_category_form': add_category_form},
                    context_instance=RequestContext(request))

        elif request.POST['submit'] == 'Apply':
            formset = forms.CategoryFormSet(request.POST, request.FILES,
                                            queryset=categories)
            if formset.is_valid():
                formset.save()
            action = request.POST['action']
            if action == 'delete':
                for category in categories:
                    category.delete()
            return HttpResponseRedirect(request.path)
