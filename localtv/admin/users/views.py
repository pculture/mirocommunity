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

from localtv.admin.users.forms import ProfileForm
from localtv.utils import get_profile_model


Profile = get_profile_model()


class UserProfileUpdateView(UpdateView):
    template_name = 'localtv/admin/users/profile.html'
    form_class = ProfileForm

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return self.success_url or reverse('localtv_admin_profile')