from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import simplejson

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.templatetags.editable_widget import WIDGET_DIRECTORY, \
    get_display_content

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

        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'SUCCESS',
                 'display_html': get_display_content(obj, field),
                 'input_html': edit_form.as_ul()}))
    else:
        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'FAIL',
                 'display_html': get_display_content(obj, field),
                 'input_html': edit_form.as_ul()}))
