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

from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect

from localtv.decorators import require_site_admin
from localtv.templatetags.editable_widget import WIDGET_DIRECTORY, \
    editable_widget

@require_site_admin
@csrf_protect
def edit_field(request, id, model=None, field=None):
    if model is None or field is None:
        raise RuntimeError('must provide a model and a field')
    obj = get_object_or_404(
        model,
        id=id)

    edit_form = WIDGET_DIRECTORY[model][field]['form'](request.POST,
                                                       request.FILES,
                                                       instance=obj)

    if edit_form.is_valid():
        edit_form.save()
        Response = HttpResponse
    else:
        Response = HttpResponseForbidden

    widget = editable_widget(request, obj, field, form=edit_form)
    return Response(widget, content_type='text/html')
