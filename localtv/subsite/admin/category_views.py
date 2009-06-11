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
    if request.method == 'GET':
        add_form = forms.AddCategoryForm()
        return render_to_response('localtv/subsite/admin/categories.html',
                                  {'categories': categories,
                                   'add_form': add_form},
                                  context_instance=RequestContext(request))
    else:
        category = Category(site=sitelocation.site)
        add_form = forms.AddCategoryForm(request.POST, instance=category)
        if add_form.is_valid():
            try:
                add_form.save()
            except IntegrityError:
                add_form._errors['__all__'] = 'There was an error adding this category.  Does it already exist?'
            else:
                return HttpResponseRedirect(request.path)

        return render_to_response('localtv/subsite/admin/categories.html',
                                  {'categories': categories,
                                   'add_form': add_form},
                                  context_instance=RequestContext(request))
