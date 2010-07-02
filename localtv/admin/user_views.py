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

from django.db.models import Count, Q
from django.conf import settings
from django.contrib.auth.models import User, UNUSABLE_PASSWORD
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.admin import forms
from localtv.util import sort_header

@require_site_admin
@get_sitelocation
@csrf_protect
def users(request, sitelocation=None):
    sort = request.GET.get('sort', 'username')
    headers = [
        sort_header('username', 'Username', sort),
         {'label': 'Email'},
         {'label': 'Role'},
         sort_header('authored_set__count', 'Videos', sort)
        ]
    users = User.objects.all().annotate(Count('authored_set')).order_by(sort)
    if request.GET.get('show', None) != 'all':
        filters = ~(Q(password=UNUSABLE_PASSWORD) | Q(password=''))
        if 'localtv_openid' in settings.INSTALLED_APPS:
            filters = filters | ~Q(openiduser=None)
        users = users.filter(filters)
    formset = forms.AuthorFormSet(queryset=users)
    add_user_form = forms.AuthorForm()
    if request.method == 'POST':
        submit = request.POST.get('submit')
        if submit == 'Add':
            add_user_form = forms.AuthorForm(request.POST, request.FILES)
            if add_user_form.is_valid():
                add_user_form.save()
                return HttpResponseRedirect(request.path)
        else:
            formset = forms.AuthorFormSet(request.POST, request.FILES,
                                          queryset=User.objects.all())
            if formset.is_valid():
                formset.save()
                return HttpResponseRedirect(request.get_full_path())

    return render_to_response('localtv/admin/users.html',
                              {'formset': formset,
                               'add_user_form': add_user_form,
                               'headers': headers},
                              context_instance=RequestContext(request))
