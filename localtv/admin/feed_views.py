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

from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.generic import CreateView

from localtv.decorators import require_site_admin, referrer_redirect
from localtv import utils
from localtv.models import Feed, SiteSettings
from localtv.admin import forms


Profile = utils.get_profile_model()


class AddFeedView(CreateView):
    model = Feed
    form_class = forms.AddFeedForm
    template_name = 'localtv/admin/add_feed.html'
    success_url = reverse_lazy('localtv_admin_manage_page')

    def get_form_kwargs(self):
        kwargs = super(AddFeedView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


add_feed = require_site_admin(csrf_protect(AddFeedView.as_view()))


@referrer_redirect
@require_site_admin
def feed_auto_approve(request, feed_id):
    feed = get_object_or_404(
        Feed,
        id=feed_id,
        site=SiteSettings.objects.get_current().site)

    feed.auto_approve = not request.GET.get('disable')
    feed.save()

    return HttpResponse('SUCCESS')
