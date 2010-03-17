# Copyright 2010 - Participatory Culture Foundation
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

from django.contrib.flatpages.models import FlatPage
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.admin import forms

@require_site_admin
@get_sitelocation
def index(request, sitelocation=None):
    headers = [
        {'label': 'Page Name'},
        {'label': 'URL'}]
    flatpages = FlatPage.objects.filter(sites=sitelocation.site)
    formset = forms.FlatPageFormSet(queryset=flatpages)

    form = forms.FlatPageForm()
    if request.method == 'GET':
        return render_to_response('localtv/admin/flatpages.html',
                                  {'formset': formset,
                                   'form': form,
                                   'headers': headers},
                                  context_instance=RequestContext(request))
    else:
        if request.POST['submit'] == 'Add':
            form = forms.FlatPageForm(request.POST)

            if form.is_valid():
                flatpage = form.save()
                flatpage.sites.add(sitelocation.site)
                return HttpResponseRedirect(request.path + '?successful')

            return render_to_response('localtv/admin/flatpages.html',
                                      {'formset': formset,
                                       'form': form,
                                       'headers': headers},
                                      context_instance=RequestContext(request))
        elif request.POST['submit'] == 'Save':
            formset = forms.FlatPageFormSet(request.POST,
                                            queryset=flatpages)
            if formset.is_valid():
                formset.save()
                return HttpResponseRedirect(request.path + '?successful')
            else:
                return render_to_response(
                    'localtv/admin/flatpages.html',
                    {'formset': formset,
                     'form': form,
                     'headers': headers},
                    context_instance=RequestContext(request))

        elif request.POST['submit'] == 'Apply':
            formset = forms.FlatPageFormSet(request.POST,
                                            queryset=flatpages)
            if formset.is_valid():
                formset.save()
            action = request.POST['action']
            if action == 'delete':
                for data in  formset.cleaned_data:
                    if data['BULK']:
                        data['id'].delete()
            return HttpResponseRedirect(request.path + '?successful')
