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

from django.db.models import Count, Q
from django.conf import settings
from django.contrib.auth.models import User, UNUSABLE_PASSWORD
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator, EmptyPage

from localtv.decorators import require_site_admin
from localtv.admin import forms
from localtv.utils import SortHeaders

def _filter_just_humans():
    filters = ~(Q(password=UNUSABLE_PASSWORD) | Q(password=''))
    if 'socialauth' in settings.INSTALLED_APPS:
        filters = filters | ~Q(authmeta=None)
    return filters
    

@require_site_admin
@csrf_protect
def users(request, formset_class=forms.AuthorFormSet,
          form_class=forms.AuthorForm):
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

    # Display only the appropriate page. Put 50 on each page at a time.
    user_paginator = Paginator(users, 50)
    try:
        page = user_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        page = user_paginator.page(user_paginator.num_pages)

    formset = formset_class(queryset=page.object_list)
    add_user_form = form_class()
    if request.method == 'POST':
        if not request.POST.get('form-TOTAL_FORMS'):
            add_user_form = form_class(request.POST, request.FILES)
            if add_user_form.is_valid():
                add_user_form.save()
                return HttpResponseRedirect(request.path)
        else:
            formset = formset_class(request.POST, request.FILES,
                                          queryset=User.objects.all())
            if formset.is_valid():
                formset.save()
                return HttpResponseRedirect(request.get_full_path())

    return render_to_response('localtv/admin/users.html',
                              {'formset': formset,
                               'add_user_form': add_user_form,
                               'page': page,
                               'headers': headers},
                              context_instance=RequestContext(request))
