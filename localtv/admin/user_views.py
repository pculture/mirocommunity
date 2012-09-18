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
from django.core.urlresolvers import reverse
from django.views.generic import CreateView, UpdateView, ListView
from django.utils.translation import ugettext as _

from localtv.admin import forms
from localtv.models import SiteSettings
from localtv.utils import SortHeaders

def _filter_just_humans():
    filters = ~(Q(password=UNUSABLE_PASSWORD) | Q(password=''))
    if 'socialauth' in settings.INSTALLED_APPS:
        filters = filters | ~Q(authmeta=None)
    return filters


class UserListView(ListView):
    model = User
    paginate_by = 50
    template_name = 'localtv/admin/users/list.html'
    context_object_name = 'users'

    def get_queryset(self):
        self.headers = SortHeaders(self.request, (
            (_('Username'), 'username'),
            (_('Email'), None),
            (_('Role'), None),
            (_('Videos'), 'video_count')
        ))
        qs = super(UserListView, self).get_queryset()
        qs = qs.annotate(video_count=Count('authored_set'))
        qs = qs.order_by(self.headers.order_by())
        show = self.request.GET.get('show')
        if show == 'humans':
            qs = qs.filter(_filter_just_humans())
        elif show == 'nonhumans':
            qs = qs.exclude(_filter_just_humans())
        return qs

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update({
            'site_admins': set(SiteSettings.objects.get_current().admins.all()),
            'headers': self.headers,
        })
        return context


class UserCreateView(CreateView):
    template_name = 'localtv/admin/users/create.html'
    form_class = forms.AuthorForm

    def get_success_url(self):
        return reverse('localtv_admin_users_update',
                       kwargs={'pk': self.object.pk})


class UserUpdateView(UpdateView):
    template_name = 'localtv/admin/users/update.html'
    form_class = forms.AuthorForm
    model = User
    context_object_name = 'user'

    def get_success_url(self):
        return reverse('localtv_admin_users_update',
                        kwargs={'pk': self.object.pk})
