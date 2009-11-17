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

import datetime

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from localtv import models
from localtv.decorators import get_sitelocation, require_site_admin
from localtv.admin import forms

@require_site_admin
@get_sitelocation
def edit_video(request, sitelocation=None):
    video_id = request.GET.get('video_id') or request.POST.get('video_id')
    video = get_object_or_404(
        models.Video, pk=video_id, site=sitelocation.site)

    if request.method == 'GET':
        edit_video_form = forms.EditVideoForm(instance=video)
        return render_to_response(
            'localtv/admin/edit_video_form.html',
            {'edit_video_form': edit_video_form},
            context_instance=RequestContext(request))
    else:
        edit_video_form = forms.EditVideoForm(request.POST, request.FILES,
                                              instance=video)
        if edit_video_form.is_valid():
            edit_video_form.save()

            if 'redirect' in request.POST:
                return HttpResponseRedirect(request.POST['redirect'])

            return render_to_response(
                'localtv/admin/edit_video_form.html',
                {'edit_video_form': edit_video_form,
                 'successful_edit': True},
                context_instance=RequestContext(request))

        else:
            return render_to_response(
                'localtv/admin/edit_video_form.html',
                {'edit_video_form': edit_video_form},
                context_instance=RequestContext(request))
