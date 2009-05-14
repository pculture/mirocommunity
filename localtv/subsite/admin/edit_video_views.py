from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404

from localtv import models
from localtv.decorators import get_sitelocation, require_site_admin
from localtv.subsite.admin import forms

@require_site_admin
@get_sitelocation
def edit_video(request, sitelocation=None):
    video_id = request.GET.get('video_id') or request.POST.get('video_id')
    video = get_object_or_404(
        models.Video, pk=video_id, site=sitelocation.site)

    if request.method == 'GET':
        openid_user = request.session.get('openid_localtv')
        edit_video_form = forms.EditVideoForm.create_from_video(video)
        return render_to_response(
            'localtv/subsite/admin/edit_video_form.html',
            {'edit_video_form': edit_video_form},
            context_instance=RequestContext(request))
    else:
        openid_user = request.session.get('openid_localtv')
        edit_video_form = forms.EditVideoForm(request.POST)
        if edit_video_form.is_valid():
            video.name = edit_video_form.cleaned_data['name']
            video.description = edit_video_form.cleaned_data['description']
            video.website_url = edit_video_form.cleaned_data['website_url']
            video.save()

            edit_video_form = forms.EditVideoForm.create_from_video(video)

            return render_to_response(
                'localtv/subsite/admin/edit_video_form.html',
                {'edit_video_form': edit_video_form,
                 'successful_edit': True},
                context_instance=RequestContext(request))

        else:
            return render_to_response(
                'localtv/subsite/admin/edit_video_form.html',
                {'edit_video_form': edit_video_form},
                context_instance=RequestContext(request))


@require_site_admin
@get_sitelocation
def reject_video(request, sitelocation=None):
    video_id = request.GET.get('video_id')
    video = get_object_or_404(
        models.Video, pk=video_id, site=sitelocation.site)
    video.status = models.VIDEO_STATUS_REJECTED
    video.save()

    return HttpResponse('SUCCESS')
