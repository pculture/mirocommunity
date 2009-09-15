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

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404

from localtv.subsite.admin import forms
from localtv.decorators import get_sitelocation, require_site_admin

def redirect():
    return HttpResponseRedirect(reverse('localtv_admin_edit_design'))

def render_edit_design(request, context):
        return render_to_response(
            "localtv/subsite/admin/edit_design.html",
            context,
            context_instance=RequestContext(request))

@require_site_admin
@get_sitelocation
def edit_design(request, sitelocation=None):
    context = {'title_form': forms.EditTitleForm.create_from_sitelocation(sitelocation),
               'sidebar_form': forms.EditSidebarForm.create_from_sitelocation(sitelocation),
               'misc_form': forms.EditMiscDesignForm.create_from_sitelocation(sitelocation)}
    if request.method == 'GET':
        return render_edit_design(request, context)
    else:
        if 'type_title' in request.POST:
            form = forms.EditTitleForm(request.POST)
            if form.is_valid():
                form.save_to_sitelocation(sitelocation)
                return redirect()
            else:
                context['title_form'] = form
                return render_edit_design(request, context)
        elif 'type_sidebar' in request.POST:
            form = forms.EditSidebarForm(request.POST)
            if form.is_valid():
                form.save_to_sitelocation(sitelocation)
                return redirect()
            else:
                context['sidebar_form'] = form
                return render_edit_design(request, context)
        elif 'type_misc' in request.POST:
            form = forms.EditMiscDesignForm(request.POST, request.FILES)
            if form.is_valid():
                form.save_to_sitelocation(sitelocation)
                return redirect()
            else:
                context['misc_form'] = form
                return render_edit_design(request, context)
        elif 'delete_background' in request.POST:
            if sitelocation.background:
                sitelocation.background.delete()
            return redirect()
        else:
            raise Http404
