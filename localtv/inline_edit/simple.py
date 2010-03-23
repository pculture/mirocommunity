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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import simplejson

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.templatetags.editable_widget import WIDGET_DIRECTORY, \
    editable_widget

@require_site_admin
@get_sitelocation
def edit_field(request, id, sitelocation=None, model=None, field=None):
    if model is None or field is None:
        raise RuntimeError('must provide a model and a field')
    obj = get_object_or_404(
        model,
        id=id,
        site=sitelocation.site)

    edit_form = WIDGET_DIRECTORY[model][field]['form'](request.POST,
                                                       instance=obj)

    if edit_form.is_valid():
        edit_form.save()
        status = 'SUCCESS'
    else:
        status = 'FAIL'

    widget = editable_widget(obj, field, form=edit_form)

    return HttpResponse(
        simplejson.dumps(
            {'post_status': status,
             'widget': widget}))
