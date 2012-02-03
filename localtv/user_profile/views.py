# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

from localtv.user_profile import forms

@login_required
@csrf_protect
def profile(request):
    if request.method == 'POST':
        form = forms.ProfileForm(request.POST, request.FILES,
                                 instance=request.user)
        if form.is_valid():
            user = form.save()
            if request.POST.get('delete_logo'):
                profile = user.get_profile()
                if profile.logo:
                    profile.logo.delete()
            return HttpResponseRedirect(request.path)
    else:
        form = forms.ProfileForm(instance=request.user)

    return render_to_response('localtv/user_profile/edit.html',
                              {'form': form},
                              context_instance=RequestContext(request))

@login_required
@csrf_protect
def notifications(request):
    if request.method == 'POST':
        form = forms.NotificationsForm(request.POST,
                                 instance=request.user)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.path)
    else:
        form = forms.NotificationsForm(instance=request.user)

    return render_to_response('localtv/user_profile/notifications.html',
                              {'form': form},
                              context_instance=RequestContext(request))
