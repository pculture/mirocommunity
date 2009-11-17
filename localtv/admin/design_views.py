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

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404

from localtv.admin import forms
from localtv.decorators import get_sitelocation, require_site_admin

def redirect():
    return HttpResponseRedirect(reverse('localtv_admin_edit_design'))

def render_edit_design(request, context):
        return render_to_response(
            "localtv/admin/edit_design.html",
            context,
            context_instance=RequestContext(request))

@require_site_admin
@get_sitelocation
def edit_design(request, sitelocation=None):
    context = {'title_form': forms.EditTitleForm.create_from_sitelocation(
            sitelocation),
               'sidebar_form': forms.EditSidebarForm.create_from_sitelocation(
            sitelocation),
               'misc_form': forms.EditMiscDesignForm.create_from_sitelocation(
            sitelocation),
               'comment_form': forms.EditCommentsForm(instance=sitelocation)}

    if request.method == 'POST':
        errors = False
        title_form = forms.EditTitleForm(request.POST)
        if title_form.is_valid():
            title_form.save_to_sitelocation(sitelocation)
        else:
            errors = True
            context['title_form'] = title_form
        sidebar_form = forms.EditSidebarForm(request.POST)
        if sidebar_form.is_valid():
                sidebar_form.save_to_sitelocation(sitelocation)
        else:
            errors = True
            context['sidebar_form'] = sidebar_form
        misc_form = forms.EditMiscDesignForm(request.POST, request.FILES)
        if misc_form.is_valid():
            misc_form.save_to_sitelocation(sitelocation)
        else:
            errors = True
            context['misc_form'] = misc_form
        comment_form = forms.EditCommentsForm(request.POST,
                                               instance=sitelocation)
        if comment_form.is_valid():
            comment_form.save()
        else:
            errors = True
            context['comment_form'] = comment_form

        if 'delete_background' in request.POST:
            if sitelocation.background:
                sitelocation.background.delete()

        if not errors:
            return redirect()

    return render_edit_design(request, context)
