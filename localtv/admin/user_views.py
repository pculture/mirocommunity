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

from localtv.decorators import require_site_admin
from localtv.admin import forms
from localtv.util import SortHeaders

def _filter_just_humans():
    filters = ~(Q(password=UNUSABLE_PASSWORD) | Q(password=''))
    if 'socialauth' in settings.INSTALLED_APPS:
        filters = filters | ~Q(authmeta=None)
    return filters
    

@require_site_admin
@csrf_protect
def users(request):
    headers = SortHeaders(request, (
            ('Username', 'username'),
            ('Email', None),
            ('Role', None),
            ('Videos', 'authored_set__count')))

    users = User.objects.all().annotate(Count('authored_set'))
    users = users.order_by(headers.order_by())
    if request.GET.get('show', None) != 'all':
        filters = _filter_just_humans()
        users = users.filter(filters)
    formset = forms.AuthorFormSet(queryset=users)
    add_user_form = forms.AuthorForm()
    if request.method == 'POST':
        if not request.POST.get('form-TOTAL_FORMS'):
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
