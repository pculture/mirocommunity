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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import simplejson

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.inline_edit import forms
from localtv.models import Video
from localtv.templatetags.editable_widget import editable_widget

@require_site_admin
@get_sitelocation
def editors_comment(request, id, sitelocation=None):
    obj = get_object_or_404(
        Video,
        id=id,
        site=sitelocation.site)

    edit_form = forms.VideoEditorsComment(request.POST, instance=obj)

    if edit_form.is_valid():
        comment = edit_form.save(commit=False)
        if comment:
            comment.site = sitelocation.site
            comment.user = request.user
            comment.save()
            edit_form.save_m2m()
        status = 'SUCCESS'
    else:
        status = 'FAIL'

    return HttpResponse(
        simplejson.dumps(
            {'post_status': status,
             'widget': editable_widget(obj, 'editors_comment',
                                       form=edit_form)}))

