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

from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from localtv.admin.base import CRUDSection, registry
from localtv.admin.users.forms import AdminProfileForm
from localtv.utils import get_profile_model


Profile = get_profile_model()


class UserSection(CRUDSection):
    url_prefix = 'users'
    navigation_text = _("Users")

    model = Profile
    create_form_class = AdminProfileForm
    update_form_class = AdminProfileForm


registry.register(UserSection)