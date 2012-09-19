from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

from localtv.models import Video, SiteSettings
from localtv.decorators import require_site_admin
from localtv.admin import forms

@require_site_admin
@csrf_protect
def edit_video(request):
    video_id = request.GET.get('video_id') or request.POST.get('video_id')
    video = get_object_or_404(
        Video, pk=video_id, site=SiteSettings.objects.get_current().site)

    if request.method == 'GET':
        edit_video_form = forms.EditVideoForm(instance=video)
        return render_to_response(
            'localtv/admin/edit_video_form.html',
            {'edit_video_form': edit_video_form},
            context_instance=RequestContext(request))
    else:
        edit_video_form = forms.EditVideoForm(request.POST, request.FILES,
                                              instance=video)
        if edit_video_form.is_valid():
            edit_video_form.save()

            if 'redirect' in request.POST:
                return HttpResponseRedirect(request.POST['redirect'])

            return render_to_response(
                'localtv/admin/edit_video_form.html',
                {'edit_video_form': edit_video_form,
                 'successful_edit': True},
                context_instance=RequestContext(request))

        else:
            return render_to_response(
                'localtv/admin/edit_video_form.html',
                {'edit_video_form': edit_video_form},
                context_instance=RequestContext(request))
