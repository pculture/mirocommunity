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
import time
import urllib
import urlparse

from django.core.urlresolvers import reverse
from django.core import cache
from django.db.models import Q
from django.core.validators import URLValidator
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

from localtv import utils
from localtv.decorators import request_passes_test
from localtv.models import SiteLocation, Video
from localtv.signals import submit_finished
from localtv.submit_video import forms
from localtv.submit_video.utils import is_video_url

url_re = URLValidator.regex

def _check_submit_permissions(request):
    sitelocation = SiteLocation.objects.get_current()
    if not sitelocation.submission_requires_login:
        return True
    else:
        if sitelocation.display_submit_button:
            return request.user.is_authenticated() and request.user.is_active
        else:
            return request.user_is_admin()


def submit_lock(func):
    def wrapper(request, *args, **kwargs):
        if request.method != 'POST':
            return func(request, *args, **kwargs)
        cache_key = 'submit_lock.%s.%s.%s' % (
            SiteLocation.objects.get_current().site.domain,
            request.path,
            request.POST['url'])
        while True:
            stored = cache.cache.add(cache_key, 'locked', 20)
            if stored:
                # got the lock
                break
            time.sleep(0.25)
        response = func(request, *args, **kwargs)
        # release the lock
        cache.cache.delete(cache_key)
        return response
    return wrapper


@request_passes_test(_check_submit_permissions)
@csrf_protect
def submit_video(request):
    sitelocation = SiteLocation.objects.get_current()
    if not (request.user_is_admin() or sitelocation.display_submit_button):
        raise Http404

    # Extract construction hint, if it exists.
    # This is a hint that plugins can use to slightly change the behavior
    # of the video submission forms.
    construction_hint = (request.POST.get('construction_hint', None) or
                         request.GET.get('construction_hint', None))

    url = request.POST.get('url') or request.GET.get('url', '')

    if request.method == "GET" and not url:
        submit_form = forms.SubmitVideoForm(
            construction_hint=construction_hint)
        return render_to_response(
            'localtv/submit_video/submit.html',
            {'form': submit_form},
            context_instance=RequestContext(request))
    else:
        url = urlparse.urldefrag(url)[0]
        submit_form = forms.SubmitVideoForm({'url': url or ''})
        if submit_form.is_valid():
            existing = Video.objects.filter(
                Q(website_url=submit_form.cleaned_data['url']) |
                Q(file_url=submit_form.cleaned_data['url']),
                site=sitelocation.site)
            existing.rejected().delete()
            if existing.count():
                if request.user_is_admin():
                    # even if the video was rejected, an admin submitting it
                    # should make it approved
                    # FIXME: This initiates a new query against the database -
                    # so the rejected videos which were deleted will not be
                    # marked approved.
                    for v in existing.exclude(
                        status=Video.ACTIVE):
                        v.user = request.user
                        v.status = Video.ACTIVE
                        v.when_approved = datetime.datetime.now()
                        v.save()
                    return HttpResponseRedirect(
                        reverse('localtv_submit_thanks',
                                args=[existing[0].pk]))
                else:
                    # pick the first approved video to point the user at
                    videos = existing.active()
                    if videos.count():
                        video = videos[0]
                    else:
                        video = None
                    return render_to_response(
                        'localtv/submit_video/submit.html',
                        {'form': forms.SubmitVideoForm(
                                construction_hint=construction_hint),
                         'was_duplicate': True,
                         'video': video},
                        context_instance=RequestContext(request))

            vidscraper_video = utils.get_vidscraper_video(
                submit_form.cleaned_data['url'])

            get_dict = {'url': submit_form.cleaned_data['url']}
            if 'construction_hint' in request.GET:
                get_dict['construction_hint'] = construction_hint
            if 'bookmarklet' in request.GET:
                get_dict['bookmarklet'] = '1'
            get_params = urllib.urlencode(get_dict)
            if vidscraper_video:
                if (vidscraper_video.link and
                    vidscraper_video.link != get_dict['url']):
                    request.POST = {
                        'url': vidscraper_video.link.encode('utf8')}
                    # rerun the view, but with the canonical URL
                    return submit_video(request)

                if (vidscraper_video.embed_code
                    or (vidscraper_video.file_url
                        and not vidscraper_video.file_url_expires)):
                    return HttpResponseRedirect(
                        reverse('localtv_submit_scraped_video') + '?' +
                        get_params)

            # otherwise if it looks like a video file
            if is_video_url(submit_form.cleaned_data['url']):
                return HttpResponseRedirect(
                    reverse('localtv_submit_directlink_video')
                    + '?' + get_params)
            else:
                return HttpResponseRedirect(
                    reverse('localtv_submit_embedrequest_video')
                    + '?' + get_params)

        else:
            return render_to_response(
                'localtv/submit_video/submit.html',
                {'form': submit_form},
                context_instance=RequestContext(request))


def _submit_finish(form, *args, **kwargs):
    if form.is_valid():
        video = form.save()
        submit_finished.send(sender=video)

        #redirect to a thank you page
        return HttpResponseRedirect(reverse('localtv_submit_thanks',
                                            args=[video.pk]))

    else:
        return render_to_response(*args, **kwargs)


@request_passes_test(_check_submit_permissions)
@submit_lock
@csrf_protect
def scraped_submit_video(request):
    if not (request.REQUEST.get('url') and \
                url_re.match(request.REQUEST['url'])):
        return HttpResponseRedirect(reverse('localtv_submit_video'))

    vidscraper_video = utils.get_vidscraper_video(request.REQUEST['url'])

    url = vidscraper_video.link or request.REQUEST['url']
    sitelocation = SiteLocation.objects.get_current()
    existing =  Video.objects.filter(site=sitelocation.site,
                                     website_url=url)
    existing.rejected().delete()
    if existing.count():
        return HttpResponseRedirect(reverse('localtv_submit_thanks',
                                                args=[existing[0].id]))
    initial = dict(request.GET.items())
    if request.method == "GET":
        scraped_form = forms.ScrapedSubmitVideoForm(
            initial=initial,
            vidscraper_video=vidscraper_video)

        return render_to_response(
            'localtv/submit_video/scraped.html',
            {'video': vidscraper_video,
             'form': scraped_form},
            context_instance=RequestContext(request))

    scraped_form = forms.ScrapedSubmitVideoForm(
        request.POST,
        sitelocation=sitelocation,
        user=request.user,
        vidscraper_video=vidscraper_video)
    return _submit_finish(scraped_form,
            'localtv/submit_video/scraped.html',
            {'video': vidscraper_video,
             'form': scraped_form},
            context_instance=RequestContext(request))


@request_passes_test(_check_submit_permissions)
@submit_lock
@csrf_protect
def embedrequest_submit_video(request):
    if not (request.REQUEST.get('url') and \
                url_re.match(request.REQUEST['url'])):
        return HttpResponseRedirect(reverse('localtv_submit_video'))

    url = request.REQUEST['url']
    sitelocation = SiteLocation.objects.get_current()
    existing =  Video.objects.filter(site=sitelocation.site,
                                            website_url=url)
    existing.rejected().delete()
    if existing.count():
        return HttpResponseRedirect(reverse('localtv_submit_thanks',
                                                args=[existing[0].id]))

    vidscraper_video = utils.get_vidscraper_video(request.REQUEST['url']) or {}
    initial = {
        'url': url,
        'name': vidscraper_video.title or '',
        'description': vidscraper_video.description or '',
        'thumbnail': vidscraper_video.thumbnail_url or '',
        }
    if request.method == "GET":
        embed_form = forms.EmbedSubmitVideoForm(initial=initial)

        return render_to_response(
            'localtv/submit_video/embed.html',
            {'form': embed_form},
            context_instance=RequestContext(request))

    embed_form = forms.EmbedSubmitVideoForm(request.POST, request.FILES,
                                            sitelocation=sitelocation,
                                            user=request.user)

    return _submit_finish(embed_form,
                          'localtv/submit_video/embed.html',
                          {'form': embed_form},
                          context_instance=RequestContext(request))


@request_passes_test(_check_submit_permissions)
@submit_lock
@csrf_protect
def directlink_submit_video(request):
    if not (request.REQUEST.get('url') and \
                url_re.match(request.REQUEST['url'])):
        return HttpResponseRedirect(reverse('localtv_submit_video'))

    url = request.REQUEST['url']
    sitelocation = SiteLocation.objects.get_current()
    existing =  Video.objects.filter(Q(website_url=url)|Q(file_url=url),
                                            site=sitelocation.site)
    existing.rejected().delete()
    if existing.count():
        return HttpResponseRedirect(reverse('localtv_submit_thanks',
                                                args=[existing[0].id]))
    initial = dict(request.GET.items())
    if request.method == "GET":
        direct_form = forms.DirectSubmitVideoForm(initial=initial)

        return render_to_response(
            'localtv/submit_video/direct.html',
            {'form': direct_form},
            context_instance=RequestContext(request))

    direct_form = forms.DirectSubmitVideoForm(
        request.POST, request.FILES,
        sitelocation=sitelocation,
        user=request.user)

    return _submit_finish(direct_form,
                          'localtv/submit_video/direct.html',
                          {'form': direct_form},
                          context_instance=RequestContext(request))


def submit_thanks(request, video_id=None):
    if request.user_is_admin() and video_id:
        context = {
            'video': Video.objects.get(pk=video_id)
            }
    else:
        context = {}
    return render_to_response(
        'localtv/submit_video/thanks.html', context,
        context_instance=RequestContext(request))
