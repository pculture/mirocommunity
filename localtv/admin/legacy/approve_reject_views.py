import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseBadRequest, \
    HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, Context, loader
from django.views.decorators.csrf import csrf_protect

from localtv.decorators import require_site_admin, referrer_redirect
from localtv.models import Video, SiteSettings
from localtv.admin.legacy import feeds

from notification import models as notification

## --------------------
## Video approve/reject
## --------------------

def get_video_paginator(site_settings):
    videos = Video.objects.filter(status=Video.NEEDS_MODERATION,
                                  site=site_settings.site
                         ).order_by('when_submitted', 'when_published')

    return Paginator(videos, 10)

@require_site_admin
@csrf_protect
def approve_reject(request):
    video_paginator = get_video_paginator(SiteSettings.objects.get_current())
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        page = video_paginator.page(video_paginator.num_pages)

    return render_to_response(
        'localtv/admin/approve_reject_table.html',
        {'page_obj': page,
         'feed_secret': feeds.generate_secret(),
         'video_list': page.object_list},
        context_instance=RequestContext(request))


@require_site_admin
def preview_video(request):
    current_video = get_object_or_404(
        Video,
        id=request.GET['video_id'],
        status=Video.NEEDS_MODERATION,
        site=Site.objects.get_current())
    return render_to_response(
        'localtv/admin/video_preview.html',
        {'current_video': current_video},
        context_instance=RequestContext(request))


@referrer_redirect
@require_site_admin
def approve_video(request):
    site_settings = SiteSettings.objects.get_current()
    current_video = get_object_or_404(
        Video,
        id=request.GET['video_id'],
        site=site_settings.site)

    current_video.status = Video.PUBLISHED
    current_video.when_approved = datetime.datetime.now()

    if request.GET.get('feature'):
        current_video.last_featured = datetime.datetime.now()

    current_video.save()

    if current_video.user and current_video.user.email:
        video_approved = notification.NoticeType.objects.get(
            label="video_approved")
        if notification.should_send(current_video.user, video_approved, "1"):
            subject = '[%s] "%s" was approved!' % (
                current_video.site.name,
                current_video)
            t = loader.get_template(
                'localtv/submit_video/approval_notification_email.txt')
            c = Context({'current_video': current_video})
            message = t.render(c)
            EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL,
                         [current_video.user.email]).send(fail_silently=True)

    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
def reject_video(request):
    current_video = get_object_or_404(
        Video,
        id=request.GET['video_id'],
        site=Site.objects.get_current())
    current_video.status = Video.HIDDEN
    current_video.save()
    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
def feature_video(request):
    video_id = request.GET.get('video_id')
    site_settings = SiteSettings.objects.get_current()
    current_video = get_object_or_404(
        Video, pk=video_id, site=site_settings.site)
    if not current_video.status == Video.PUBLISHED:
        current_video.status = Video.PUBLISHED
        current_video.when_approved = datetime.datetime.now()
    current_video.last_featured = datetime.datetime.now()
    current_video.save()

    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
def unfeature_video(request):
    video_id = request.GET.get('video_id')
    current_video = get_object_or_404(
        Video, pk=video_id, site=Site.objects.get_current())
    current_video.last_featured = None
    current_video.save()

    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
@csrf_protect
def reject_all(request):
    video_paginator = get_video_paginator(SiteSettings.objects.get_current())
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        return HttpResponseBadRequest(
            'Page number request exceeded available pages')

    for video in page.object_list:
        video.status = Video.HIDDEN
        video.save()

    return HttpResponse('SUCCESS')

@referrer_redirect
@require_site_admin
@csrf_protect
def approve_all(request):
    site_settings = SiteSettings.objects.get_current()
    video_paginator = get_video_paginator(site_settings)
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        return HttpResponseBadRequest(
            'Page number request exceeded available pages')

    for video in page.object_list:
        video.status = Video.PUBLISHED
        video.when_approved = datetime.datetime.now()
        video.save()

    return HttpResponse('SUCCESS')

@require_site_admin
@csrf_protect
def clear_all(request):
    videos = Video.objects.filter(status=Video.NEEDS_MODERATION,
                                  site=Site.objects.get_current())
    if request.POST.get('confirm') == 'yes':
        for video in videos:
            video.status = Video.HIDDEN
            video.save()
        return HttpResponseRedirect(reverse('localtv_admin_approve_reject'))
    else:
        return render_to_response('localtv/admin/clear_confirm.html',
                                  {'videos': videos},
                                  context_instance=RequestContext(request))
