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

import re

from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.utils.encoding import force_unicode
from django.views.decorators.csrf import csrf_protect

from localtv.decorators import require_site_admin
from localtv import models
from localtv.util import SortHeaders, MockQueryset
from localtv.admin import forms

@require_site_admin
@csrf_protect
def upgrade(request):
    data = {}
    data['site_location'] = models.SiteLocation.objects.get_current()
    return render_to_response('localtv/admin/upgrade.html', data,
                              context_instance=RequestContext(request))
