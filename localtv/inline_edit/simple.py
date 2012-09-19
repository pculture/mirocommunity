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
