from django.shortcuts import render_to_response
from django.template.context import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv import models
from localtv.subsite.admin import forms

@get_sitelocation
@require_site_admin
def bulk_edit(request, sitelocation=None):
    videos = models.Video.objects.filter(
        status=models.VIDEO_STATUS_ACTIVE,
        site=sitelocation.site).order_by('name')

    if request.method == 'POST':
        return

    else:
        formset = forms.VideoFormSet(queryset=videos)
        return render_to_response('localtv/subsite/admin/bulk_edit.html',
                                  {'formset': formset},
                                  context_instance=RequestContext(request))
