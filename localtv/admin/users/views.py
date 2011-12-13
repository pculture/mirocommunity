# Copyright 2010 - Participatory Culture Foundation
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

from django.core.urlresolvers import reverse
from django.views.generic import UpdateView

from localtv.admin.users.forms import UserProfileForm
from localtv.utils import get_profile_model


Profile = get_profile_model()


# This was copied from user_views.py. Not sure yet how filters will be
# implemented, but once they are - this should probably be one of them.
def _human_filter():
    """
    Returns a Q object which can be used for fetching "human" users - i.e. users
    with a real password or (if socialauth is installed) valid socialauth data.

    """
    filters = ~(Q(password=UNUSABLE_PASSWORD) | Q(password=''))
    if 'socialauth' in settings.INSTALLED_APPS:
        filters = filters | ~Q(authmeta=None)
    return filters


class UserProfileUpdateView(UpdateView):
    template_name = 'localtv/admin/users/profile.html'
    form_class = UserProfileForm

    def get_object(self):
        return Profile.objects.get_or_create(user=self.request.user)[0]

    def get_success_url(self):
        return self.success_url or reverse('localtv_admin_profile')