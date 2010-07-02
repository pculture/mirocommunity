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
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect

from localtv.admin import forms
from localtv.decorators import get_sitelocation, require_site_admin

@require_site_admin
@get_sitelocation
@csrf_protect
def edit_settings(request, sitelocation):
    form = forms.EditSettingsForm(instance=sitelocation)

    if request.method == 'POST':
        form = forms.EditSettingsForm(request.POST, request.FILES,
                                      instance=sitelocation)
        if form.is_valid():
            sitelocation = form.save()
            if request.POST.get('delete_background'):
                if sitelocation.background:
                    sitelocation.background.delete()
            return HttpResponseRedirect(
                reverse('localtv_admin_settings'))

    return render_to_response(
        "localtv/admin/edit_settings.html",
        {'form': form},
        context_instance=RequestContext(request))
