import datetime

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

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
        edit_video_form = forms.EditVideoForm.create_from_video(video)
        return render_to_response(
            'localtv/subsite/admin/edit_video_form.html',
            {'edit_video_form': edit_video_form},
            context_instance=RequestContext(request))
    else:
        edit_video_form = forms.EditVideoForm(request.POST, request.FILES)
        if edit_video_form.is_valid():
            video.name = edit_video_form.cleaned_data['name']
            video.description = edit_video_form.cleaned_data.get('description')
            video.website_url = edit_video_form.cleaned_data.get('website_url')
            video.categories = edit_video_form.cleaned_data.get('categories')
            video.authors = edit_video_form.cleaned_data.get('authors')
            thumbnail = edit_video_form.cleaned_data.get('thumbnail')
            if thumbnail:
                video.thumbnail_url = '' # since we're no longer using that URL
                                         # for a thumbnail
                video.save_thumbnail_from_file(thumbnail)
            video.save()

            edit_video_form = forms.EditVideoForm.create_from_video(video)

            if 'redirect' in request.POST:
                return HttpResponseRedirect(request.POST['redirect'])

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
