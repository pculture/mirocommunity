from django.contrib.flatpages.models import FlatPage
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

from localtv.admin import forms
from localtv.decorators import require_site_admin
from localtv.models import SiteSettings


@require_site_admin
@csrf_protect
def index(request):
    headers = [
        {'label': 'Page Name'},
        {'label': 'URL'}]
    site_settings = SiteSettings.objects.get_current()
    flatpages = FlatPage.objects.filter(sites=site_settings.site)
    formset = forms.FlatPageFormSet(queryset=flatpages)

    form = forms.FlatPageForm()
    if request.method == 'GET':
        return render_to_response('localtv/admin/flatpages.html',
                                  {'formset': formset,
                                   'form': form,
                                   'headers': headers},
                                  context_instance=RequestContext(request))
    else:
        if request.POST.get('submit') == 'Add':
            form = forms.FlatPageForm(request.POST)

            if form.is_valid():
                flatpage = form.save()
                flatpage.sites.add(site_settings.site)
                return HttpResponseRedirect(request.path + '?successful')

            return render_to_response('localtv/admin/flatpages.html',
                                      {'formset': formset,
                                       'form': form,
                                       'headers': headers},
                                      context_instance=RequestContext(request))
        else:
            formset = forms.FlatPageFormSet(request.POST,
                                            queryset=flatpages)
            if formset.is_valid():
                formset.save()
                action = request.POST.get('bulk_action')
                if action == 'delete':
                    for data in  formset.cleaned_data:
                        if data['BULK']:
                            data['id'].delete()
                return HttpResponseRedirect(request.path + '?successful')
            else:
                return render_to_response(
                    'localtv/admin/flatpages.html',
                    {'formset': formset,
                     'form': form,
                     'headers': headers},
                    context_instance=RequestContext(request))
