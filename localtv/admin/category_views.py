from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

from localtv.decorators import require_site_admin
from localtv.models import Category, SiteSettings
from localtv.admin import forms


@require_site_admin
@csrf_protect
def categories(request):
    site_settings = SiteSettings.objects.get_current()
    categories = Category.objects.filter(site=site_settings.site)
    formset = forms.CategoryFormSet(queryset=categories)
    headers = [
        {'label': 'Category'},
        {'label': 'Description'},
        {'label': 'Slug'},
        {'label': 'Videos'}
    ]
    add_category_form = forms.CategoryForm()
    add_category_form.fields['parent'].queryset = formset._qs_cache['parent']
    if request.method == 'POST':
        if not request.POST.get('form-TOTAL_FORMS'):
            category = Category(site=site_settings.site)
            add_category_form = forms.CategoryForm(request.POST,
                                                   request.FILES,
                                                   instance=category)
            if add_category_form.is_valid():
                add_category_form.save()
                return HttpResponseRedirect(request.path + '?successful')

        else:
            formset = forms.CategoryFormSet(request.POST, request.FILES,
                                            queryset=categories)
            if formset.is_valid():
                formset.save()
                action = request.POST.get('bulk_action')
                if action == 'delete':
                    for data in  formset.cleaned_data:
                        if data['BULK']:
                            category = data['id']
                            for child in category.child_set.all():
                                # reset children to no parent
                                child.parent = None
                                child.save()
                            data['id'].delete()
                return HttpResponseRedirect(request.path + '?successful')

    return render_to_response('localtv/admin/categories.html',
                              {'formset': formset,
                               'headers': headers,
                               'add_category_form': add_category_form},
                              context_instance=RequestContext(request))
    
