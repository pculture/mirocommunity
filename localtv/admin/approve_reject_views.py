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

from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin, \
    referrer_redirect
from localtv import models
from localtv.subsite.admin import feeds
from django.http import HttpResponse, HttpResponseBadRequest, \
    HttpResponseRedirect


## --------------------
## Video approve/reject
## --------------------

def get_video_paginator(sitelocation):
    videos = models.Video.objects.filter(
        status=models.VIDEO_STATUS_UNAPPROVED,
        site=sitelocation.site).order_by(
        'when_submitted', 'when_published')

    return Paginator(videos, 10)

@require_site_admin
@get_sitelocation
def approve_reject(request, sitelocation=None):
    if request.method == "GET":
        video_paginator = get_video_paginator(sitelocation)
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
    else:
        pass


@require_site_admin
@get_sitelocation
def preview_video(request, sitelocation=None):
    current_video = get_object_or_404(
        models.Video,
        id=request.GET['video_id'],
        status=models.VIDEO_STATUS_UNAPPROVED,
        site=sitelocation.site)
    return render_to_response(
        'localtv/admin/video_preview.html',
        {'current_video': current_video},
        context_instance=RequestContext(request))


@referrer_redirect
@require_site_admin
@get_sitelocation
def approve_video(request, sitelocation=None):
    current_video = get_object_or_404(
        models.Video,
        id=request.GET['video_id'],
        site=sitelocation.site)
    current_video.status = models.VIDEO_STATUS_ACTIVE
    current_video.when_approved = datetime.datetime.now()

    if request.GET.get('feature'):
        current_video.last_featured = datetime.datetime.now()

    current_video.save()
    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
@get_sitelocation
def reject_video(request, sitelocation=None):
    current_video = get_object_or_404(
        models.Video,
        id=request.GET['video_id'],
        site=sitelocation.site)
    current_video.status = models.VIDEO_STATUS_REJECTED
    current_video.save()
    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
@get_sitelocation
def feature_video(request, sitelocation=None):
    video_id = request.GET.get('video_id')
    current_video = get_object_or_404(
        models.Video, pk=video_id, site=sitelocation.site)
    if current_video.status != models.VIDEO_STATUS_ACTIVE:
        current_video.status = models.VIDEO_STATUS_ACTIVE
        current_video.when_approved = datetime.datetime.now()
    current_video.last_featured = datetime.datetime.now()
    current_video.save()

    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
@get_sitelocation
def unfeature_video(request, sitelocation=None):
    video_id = request.GET.get('video_id')
    current_video = get_object_or_404(
        models.Video, pk=video_id, site=sitelocation.site)
    current_video.last_featured = None
    current_video.save()

    return HttpResponse('SUCCESS')


@referrer_redirect
@require_site_admin
@get_sitelocation
def reject_all(request, sitelocation=None):
    video_paginator = get_video_paginator(sitelocation)
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        return HttpResponseBadRequest(
            'Page number request exceeded available pages')

    for video in page.object_list:
        video.status = models.VIDEO_STATUS_REJECTED
        video.save()

    return HttpResponse('SUCCESS')

@referrer_redirect
@require_site_admin
@get_sitelocation
def approve_all(request, sitelocation=None):
    video_paginator = get_video_paginator(sitelocation)
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        return HttpResponseBadRequest(
            'Page number request exceeded available pages')

    for video in page.object_list:
        video.status = models.VIDEO_STATUS_ACTIVE
        video.when_approved = datetime.datetime.now()
        video.save()

    return HttpResponse('SUCCESS')

@require_site_admin
@get_sitelocation
def clear_all(request, sitelocation=None):
    videos = models.Video.objects.filter(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_UNAPPROVED)
    if request.POST.get('confirm') == 'yes':
        for video in videos:
            video.status = models.VIDEO_STATUS_REJECTED
            video.save()
        return HttpResponseRedirect(reverse('localtv_admin_approve_reject'))
    else:
        return render_to_response('localtv/admin/clear_confirm.html',
                                  {'videos': videos},
                                  context_instance=RequestContext(request))
