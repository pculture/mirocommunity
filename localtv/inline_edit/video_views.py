from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect

from localtv.decorators import require_site_admin
from localtv.inline_edit import forms
from localtv.models import Video, SiteSettings
from localtv.templatetags.editable_widget import editable_widget

@require_site_admin
@csrf_protect
def editors_comment(request, id):
    site_settings = SiteSettings.objects.get_current()
    obj = get_object_or_404(
        Video,
        id=id,
        site=site_settings.site)

    edit_form = forms.VideoEditorsComment(request.POST, instance=obj)

    if edit_form.is_valid():
        comment = edit_form.save(commit=False)
        if comment:
            comment.site = site_settings.site
            comment.user = request.user
            comment.save()
            edit_form.save_m2m()
        Response = HttpResponse
    else:
        Response = HttpResponseForbidden

    return Response(
        editable_widget(request, obj, 'editors_comment',
                        form=edit_form))

