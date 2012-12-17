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

from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.generic import CreateView, UpdateView, DeleteView

from localtv.decorators import require_site_admin, referrer_redirect
from localtv import utils
from localtv.models import Feed
from localtv.admin import forms


Profile = utils.get_profile_model()


class AddFeedView(CreateView):
    model = Feed
    form_class = forms.AddFeedForm
    template_name = 'localtv/admin/sources/feed_edit.html'
    success_url = reverse_lazy('localtv_admin_manage_page')
    context_object_name = 'feed'
    initial = {'auto_approve': False}

    def get_form_kwargs(self):
        kwargs = super(AddFeedView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class EditFeedView(UpdateView):
    model = Feed
    form_class = forms.EditFeedForm
    context_object_name = 'feed'
    template_name = 'localtv/admin/sources/feed_edit.html'

    def get_success_url(self):
        return self.request.path


class DeleteFeedView(DeleteView):
    model = Feed
    success_url = reverse_lazy('localtv_admin_manage_page')

    def get(self, *args, **kwargs):
        return self.delete(*args, **kwargs)


add_feed = require_site_admin(csrf_protect(AddFeedView.as_view()))
edit_feed = require_site_admin(csrf_protect(EditFeedView.as_view()))
delete_feed = require_site_admin(csrf_protect(DeleteFeedView.as_view()))


@referrer_redirect
@require_site_admin
def feed_auto_approve(request, pk):
    feed = get_object_or_404(Feed, pk=pk, site_id=settings.SITE_ID)

    feed.auto_approve = not request.GET.get('disable')
    feed.save()

    return HttpResponse('SUCCESS')
