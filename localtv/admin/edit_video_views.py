# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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

from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

from localtv.models import Video, SiteLocation
from localtv.decorators import require_site_admin
from localtv.admin import forms

@require_site_admin
@csrf_protect
def edit_video(request):
    video_id = request.GET.get('video_id') or request.POST.get('video_id')
    video = get_object_or_404(
        Video, pk=video_id, site=SiteLocation.objects.get_current().site)

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
