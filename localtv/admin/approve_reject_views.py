# Copyright 2009 - Participatory Culture Foundation
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

import datetime

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseBadRequest, \
    HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, Context, loader
from django.views.decorators.csrf import csrf_protect

from localtv.decorators import require_site_admin, referrer_redirect
from localtv.models import Video, SiteLocation
from localtv.admin import feeds

from notification import models as notification

## --------------------
## Video approve/reject
## --------------------

def get_video_paginator(sitelocation):
    videos = Video.objects.unapproved().filter(
        site=sitelocation.site).order_by(
        'when_submitted', 'when_published')

    return Paginator(videos, 10)

@require_site_admin
@csrf_protect
def approve_reject(request):
    video_paginator = get_video_paginator(SiteLocation.objects.get_current())
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        page = video_paginator.page(video_paginator.num_pages)

    current_video = None
    if page.object_list:
        current_video = page.object_list[0]

    return render_to_response(
        'localtv/admin/approve_reject_table.html',
        {'current_video': current_video,
         'page_obj': page,
         'feed_secret': feeds.generate_secret(),
         'video_list': page.object_list},
        context_instance=RequestContext(request))


@require_site_admin
def preview_video(request):
    current_video = get_object_or_404(
        Video,
        id=request.GET['video_id'],
        status=Video.UNAPPROVED,
        site=SiteLocation.objects.get_current().site)
    return render_to_response(
        'localtv/admin/video_preview.html',
        {'current_video': current_video},
        context_instance=RequestContext(request))


@referrer_redirect
@require_site_admin
def approve_video(request):
    sitelocation = SiteLocation.objects.get_current()
    current_video = get_object_or_404(
        Video,
        id=request.GET['video_id'],
        site=sitelocation.site)

    # If the site would exceed its video allotment, then fail
    # with a HTTP 402 and a clear message about why.
    if (SiteLocation.enforce_tiers() and
        sitelocation.get_tier().remaining_videos() < 1):
        return HttpResponse(content="You are over the video limit. You will need to upgrade to approve that video.", status=402)

    current_video.status = Video.ACTIVE
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
        site=SiteLocation.objects.get_current().site)
    current_video.status = Video.REJECTED
    current_video.save()
    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
def feature_video(request):
    video_id = request.GET.get('video_id')
    sitelocation = SiteLocation.objects.get_current()
    current_video = get_object_or_404(
        Video, pk=video_id, site=sitelocation.site)
    if not current_video.is_active():
        if (SiteLocation.enforce_tiers() and
            sitelocation.get_tier().remaining_videos() < 1):
            return HttpResponse(content="You are over the video limit. You will need to upgrade to feature that video.", status=402)
        current_video.status = Video.ACTIVE
        current_video.when_approved = datetime.datetime.now()
    current_video.last_featured = datetime.datetime.now()
    current_video.save()

    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
def unfeature_video(request):
    video_id = request.GET.get('video_id')
    current_video = get_object_or_404(
        Video, pk=video_id, site=SiteLocation.objects.get_current().site)
    current_video.last_featured = None
    current_video.save()

    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
@csrf_protect
def reject_all(request):
    video_paginator = get_video_paginator(SiteLocation.objects.get_current())
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        return HttpResponseBadRequest(
            'Page number request exceeded available pages')

    for video in page.object_list:
        video.status = Video.REJECTED
        video.save()

    return HttpResponse('SUCCESS')

@referrer_redirect
@require_site_admin
@csrf_protect
def approve_all(request):
    sitelocation = SiteLocation.objects.get_current()
    video_paginator = get_video_paginator(sitelocation)
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        return HttpResponseBadRequest(
            'Page number request exceeded available pages')

    if SiteLocation.enforce_tiers():
        tier_remaining_videos = sitelocation.get_tier().remaining_videos()
        if len(page.object_list) > tier_remaining_videos:
            remaining = str(tier_remaining_videos)
            need = str(len(page.object_list))
            return HttpResponse(content=(
                    ("You are trying to approve %s videos at a time. " % need) +
                    ("However, you can approve only %s more videos under your video limit. " % remaining) +
                    ("Please upgrade your account to increase your limit, or unapprove some older videos to make space for newer ones.")), status=402)

    for video in page.object_list:
        video.status = Video.ACTIVE
        video.when_approved = datetime.datetime.now()
        video.save()

    return HttpResponse('SUCCESS')

@require_site_admin
@csrf_protect
def clear_all(request):
    videos = Video.objects.unapproved().filter(
        site=SiteLocation.objects.get_current().site)
    if request.POST.get('confirm') == 'yes':
        for video in videos:
            video.status = Video.REJECTED
            video.save()
        return HttpResponseRedirect(reverse('localtv_admin_approve_reject'))
    else:
        return render_to_response('localtv/admin/clear_confirm.html',
                                  {'videos': videos},
                                  context_instance=RequestContext(request))
