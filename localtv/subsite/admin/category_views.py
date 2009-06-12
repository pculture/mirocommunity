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
    add_form = forms.CategoryForm()
    if request.method == 'GET':
        add_form = forms.CategoryForm()
        return render_to_response('localtv/subsite/admin/categories.html',
                                  {'categories': categories,
                                   'add_form': add_form},
                                  context_instance=RequestContext(request))
    else:
        if request.POST['submit'] == 'Add':
            category = Category(site=sitelocation.site)
            add_form = forms.CategoryForm(request.POST, instance=category)
            if add_form.is_valid():
                try:
                    add_form.save()
                except IntegrityError:
                    add_form._errors = 'There was an error adding this category.  Does it already exist?'
                else:
                    return HttpResponseRedirect(request.path)

            return render_to_response('localtv/subsite/admin/categories.html',
                                      {'categories': categories,
                                       'add_form': add_form},
                                      context_instance=RequestContext(request))
        elif request.POST['submit'] == 'Save':
            invalid = False
            for category in categories:
                category.form = forms.CategoryForm(
                    request.POST,
                    prefix="edit_%s" % category.id,
                    instance=category)
                if category.form.is_valid():
                    try:
                        category.form.save()
                    except IntegrityError:
                        category.form._errors = 'There was an error editing %s. Does it already exist?' % category.name
                        invalid = True
                else:
                    invalid = True
            if invalid:
                return render_to_response('localtv/subsite/admin/categories.html',
                                          {'categories': categories,
                                           'add_form': add_form},
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
