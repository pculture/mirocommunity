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
from os import path
import urllib
import urlparse

from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.forms.fields import url_re
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv import models, util
from localtv.decorators import get_sitelocation, request_passes_test
from localtv.subsite.submit_video import forms
from localtv.templatetags.filters import sanitize

def _check_submit_permissions(request):
    sitelocation = models.SiteLocation.objects.get(
        site=Site.objects.get_current())
    user = request.user
    if not sitelocation.submission_requires_login:
        return True
    else:
        if sitelocation.display_submit_button:
            return user.is_authenticated() and user.is_active
        else:
            return sitelocation.user_is_admin(user)


@request_passes_test(_check_submit_permissions)
@get_sitelocation
def submit_video(request, sitelocation=None):
    if not (sitelocation.display_submit_button or
            sitelocation.user_is_admin(request.user)):
        raise Http404
    if request.method == "GET":
        submit_form = forms.SubmitVideoForm()
        return render_to_response(
            'localtv/subsite/submit/submit_video.html',
            {'sitelocation': sitelocation,
             'submit_form': submit_form},
            context_instance=RequestContext(request))
    else:
        submit_form = forms.SubmitVideoForm(request.POST)
        if submit_form.is_valid():
            url_filename = path.split(
                urlparse.urlsplit(
                    submit_form.cleaned_data['url'])[2])[-1]
            if models.Video.objects.filter(
                    website_url=submit_form.cleaned_data['url'],
                    site=sitelocation.site).count():
                if sitelocation.user_is_admin(request.user):
                    # even if the video was rejected, an admin submitting it
                    # should make it approved
                    for v in models.Video.objects.filter(
                        website_url=submit_form.cleaned_data['url'],
                        site=sitelocation.site).exclude(
                        status=models.VIDEO_STATUS_ACTIVE):
                        v.user = request.user
                        v.status = models.VIDEO_STATUS_ACTIVE
                        v.when_approved = datetime.datetime.now()
                        v.save()
                        return HttpResponseRedirect(
                            reverse('localtv_submit_thanks'))
                else:
                    # pick the first approved video to point the user at
                    videos = models.Video.objects.filter(
                        website_url=submit_form.cleaned_data['url'],
                        site=sitelocation.site,
                        status=models.VIDEO_STATUS_ACTIVE)
                    if videos.count():
                        video = videos[0]
                    else:
                        video = None
                    return render_to_response(
                        'localtv/subsite/submit/submit_video.html',
                        {'sitelocation': sitelocation,
                         'submit_form': forms.SubmitVideoForm(),
                         'was_duplicate': True,
                         'video': video},
                        context_instance=RequestContext(request))

            scraped_data = util.get_scraped_data(
                submit_form.cleaned_data['url'])

            get_dict = {'url': submit_form.cleaned_data['url']}
            if submit_form.cleaned_data.get('tags'):
                get_dict['tags'] = ', '.join(submit_form.cleaned_data['tags'])
            get_params = urllib.urlencode(get_dict)

            if scraped_data:
                if 'link' in scraped_data and \
                        scraped_data['link'] != get_dict['url']:
                    request.POST = dict(request.POST)
                    request.POST['url'] = scraped_data['link'].encode('utf8')
                    request.POST['tags'] = get_dict['tags'].encode('utf8')
                    # rerun the view, but with the canonical URL
                    return submit_video(request)

                if (scraped_data.get('embed')
                    or (scraped_data.get('file_url')
                        and not scraped_data.get('file_url_is_flaky'))):
                    return HttpResponseRedirect(
                        reverse('localtv_submit_scraped_video') + '?' +
                        get_params)

            # otherwise if it looks like a video file
            elif util.is_video_filename(url_filename):
                return HttpResponseRedirect(
                    reverse('localtv_submit_directlink_video')
                    + '?' + get_params)
            else:
                return HttpResponseRedirect(
                    reverse('localtv_submit_embedrequest_video')
                    + '?' + get_params)
            
        else:
            return render_to_response(
                'localtv/subsite/submit/submit_video.html',
                {'sitelocation': sitelocation,
                 'submit_form': submit_form},
                context_instance=RequestContext(request))


@request_passes_test(_check_submit_permissions)
@get_sitelocation
def scraped_submit_video(request, sitelocation=None):
    if request.method == "GET":

        if not (request.GET.get('url') or url_re.match(request.GET['url'])):
            return HttpResponseRedirect(reverse('localtv_submit_video'))

        scraped_data = util.get_scraped_data(request.GET['url'])

        scraped_form = forms.ScrapedSubmitVideoForm()
        scraped_form.set_initial(request)
        scraped_form.initial['name'] = scraped_data.get('title')
        scraped_form.initial['description'] = scraped_data.get('description')
        scraped_form.initial['thumbnail'] = scraped_data.get(
            'thumbnail_url')

        return render_to_response(
            'localtv/subsite/submit/scraped_submit_video.html',
            {'sitelocation': sitelocation,
             'scraped_form': scraped_form},
            context_instance=RequestContext(request))

    scraped_form = forms.ScrapedSubmitVideoForm(request.POST)
    if scraped_form.is_valid():
        scraped_data = util.get_scraped_data(request.POST['url'])

        if scraped_data.get('file_url_is_flaky'):
            file_url = None
        else:
            file_url = scraped_data.get('file_url', '')

        if request.user.is_authenticated():
            user = request.user
        else:
            user = None

        video = models.Video(
            name=scraped_form.cleaned_data['name'],
            site=sitelocation.site,
            description=sanitize(scraped_form.cleaned_data['description'],
                                 extra_filters=['img']),
            file_url=file_url or '',
            embed_code=scraped_data.get('embed') or '',
            flash_enclosure_url=scraped_data.get('flash_enclosure_url', ''),
            website_url=scraped_form.cleaned_data['url'],
            thumbnail_url=request.POST.get('thumbnail', ''),
            user=user,
            when_submitted=datetime.datetime.now(),
            when_published=scraped_data.get('publish_date'),
            video_service_user=scraped_data.get('user'),
            video_service_url=scraped_data.get('user_url'))


        if sitelocation.user_is_admin(request.user):
            video.when_approved = video.when_submitted
            video.status = models.VIDEO_STATUS_ACTIVE

        video.save()

        if video.thumbnail_url:
            video.save_thumbnail_from_file(
                scraped_form.cleaned_data['thumbnail'])

        tags = util.get_or_create_tags(
            scraped_form.cleaned_data.get('tags', []))
        for tag in tags:
            video.tags.add(tag)

        #redirect to a thank you page
        return HttpResponseRedirect(reverse('localtv_submit_thanks'))

    else:
        return render_to_response(
            'localtv/subsite/submit/scraped_submit_video.html',
            {'sitelocation': sitelocation,
             'scraped_form': scraped_form},
            context_instance=RequestContext(request))


@request_passes_test(_check_submit_permissions)
@get_sitelocation
def embedrequest_submit_video(request, sitelocation=None):
    if request.method == "GET":

        if not (request.GET.get('url') or url_re.match(request.GET['url'])):
            return HttpResponseRedirect(reverse('localtv_submit_video'))

        embed_form = forms.EmbedSubmitVideoForm()
        embed_form.set_initial(request)

        return render_to_response(
            'localtv/subsite/submit/embed_submit_video.html',
            {'sitelocation': sitelocation,
             'embed_form': embed_form},
            context_instance=RequestContext(request))

    embed_form = forms.EmbedSubmitVideoForm(request.POST)
    if embed_form.is_valid():

        if request.user.is_authenticated():
            user = request.user
        else:
            user = None

        video = models.Video(
            name=embed_form.cleaned_data['name'],
            site=sitelocation.site,
            description=sanitize(embed_form.cleaned_data['description'],
                                 extra_filters=['img']),
            embed_code=embed_form.cleaned_data['embed'],
            website_url=embed_form.cleaned_data.get('website_url', ''),
            thumbnail_url=request.POST.get('thumbnail', ''),
            user=user,
            when_submitted=datetime.datetime.now())

        if sitelocation.user_is_admin(request.user):
            video.when_approved = video.when_submitted
            video.status = models.VIDEO_STATUS_ACTIVE

        video.save()

        if video.thumbnail_url:
            video.save_thumbnail_from_file(
                embed_form.cleaned_data['thumbnail'])

        tags = util.get_or_create_tags(
            embed_form.cleaned_data.get('tags', []))
        for tag in tags:
            video.tags.add(tag)

        #reembed to a thank you page
        return HttpResponseRedirect(reverse('localtv_submit_thanks'))

    else:
        return render_to_response(
            'localtv/subsite/submit/embed_submit_video.html',
            {'sitelocation': sitelocation,
             'embed_form': embed_form},
            context_instance=RequestContext(request))




@request_passes_test(_check_submit_permissions)
@get_sitelocation
def directlink_submit_video(request, sitelocation=None):
    if request.method == "GET":

        if not (request.GET.get('url') or url_re.match(request.GET['url'])):
            return HttpResponseRedirect(reverse('localtv_submit_video'))

        direct_form = forms.DirectSubmitVideoForm()
        direct_form.set_initial(request)

        return render_to_response(
            'localtv/subsite/submit/direct_submit_video.html',
            {'sitelocation': sitelocation,
             'direct_form': direct_form},
            context_instance=RequestContext(request))

    direct_form = forms.DirectSubmitVideoForm(request.POST)
    if direct_form.is_valid():
        if request.user.is_authenticated():
            user = request.user
        else:
            user = None

        video = models.Video(
            name=direct_form.cleaned_data['name'],
            site=sitelocation.site,
            description=sanitize(direct_form.cleaned_data['description'],
                                 extra_filters=['img']),
            file_url=direct_form.cleaned_data['url'],
            thumbnail_url=request.POST.get('thumbnail', ''),
            website_url=direct_form.cleaned_data.get('website_url', ''),
            user=user,
            when_submitted=datetime.datetime.now())

        if sitelocation.user_is_admin(request.user):
            video.when_approved = video.when_submitted
            video.status = models.VIDEO_STATUS_ACTIVE

        video.save()

        if video.thumbnail_url:
            video.save_thumbnail_from_file(
                direct_form.cleaned_data['thumbnail'])

        tags = util.get_or_create_tags(
            direct_form.cleaned_data.get('tags', []))
        for tag in tags:
            video.tags.add(tag)

        #redirect to a thank you page
        return HttpResponseRedirect(reverse('localtv_submit_thanks'))

    else:
        return render_to_response(
            'localtv/subsite/submit/direct_submit_video.html',
            {'sitelocation': sitelocation,
             'direct_form': direct_form},
            context_instance=RequestContext(request))


@get_sitelocation
def submit_thanks(request, sitelocation=None):
    if sitelocation.user_is_admin(request.user):
        context = {
            'video': models.Video.objects.filter(site=sitelocation.site,
                                                 user=request.user).order_by(
                '-id')[0]
            }
    else:
        context = {}
    return render_to_response(
        'localtv/subsite/submit/thanks.html', context,
        context_instance=RequestContext(request))
