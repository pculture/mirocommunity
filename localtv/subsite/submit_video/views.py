import datetime
from os import path
import urllib
import urlparse

from django.core.urlresolvers import reverse
from django.forms.fields import url_re
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv import models, util
from localtv.decorators import get_sitelocation, require_active_openid
from localtv.subsite.submit_video import forms


@require_active_openid
@get_sitelocation
def submit_video(request, sitelocation=None):
    if request.method == "GET":
        submit_form = forms.SubmitVideoForm()
        return render_to_response(
            'localtv/subsite/submit/submit_video.html',
            {'sitelocation': sitelocation,
             'submit_form': submit_form,
             'was_duplicate': bool(request.GET.get('was_duplicate', False))},
            context_instance=RequestContext(request))
    else:
        submit_form = forms.SubmitVideoForm(request.POST)
        if submit_form.is_valid():
            url_filename = path.split(
                urlparse.urlsplit(
                    submit_form.cleaned_data['url'])[2])[-1]

            # if the video already exists, redirect back here with a warning.
            if models.Video.objects.filter(
                    website_url=submit_form.cleaned_data['url'],
                    site=sitelocation.site).count():
                return HttpResponseRedirect(
                    reverse('localtv_submit_video') + '?was_duplicate=true')

            scraped_data = util.get_scraped_data(
                submit_form.cleaned_data['url'])

            get_dict = {'url': submit_form.cleaned_data['url']}
            if submit_form.cleaned_data.get('tags'):
                get_dict['tags'] = ', '.join(submit_form.cleaned_data['tags'])
            get_params = urllib.urlencode(get_dict)

            if scraped_data and (
                    scraped_data.get('embed') or scraped_data.get('file_url')):
                return HttpResponseRedirect(
                    reverse('localtv_submit_scraped_video') + '?' + get_params)

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


@require_active_openid
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
        scraped_form.initial['thumbnail_url'] = scraped_data.get(
            'thumbnail_url')

        return render_to_response(
            'localtv/subsite/submit/scraped_submit_video.html',
            {'sitelocation': sitelocation,
             'scraped_form': scraped_form},
            context_instance=RequestContext(request))

    scraped_form = forms.ScrapedSubmitVideoForm(request.POST)
    if scraped_form.is_valid():
        scraped_data = util.get_scraped_data(request.POST['url'])

        video = models.Video(
            name=scraped_form.cleaned_data['name'],
            site=sitelocation.site,
            description=scraped_form.cleaned_data['description'],
            file_url=scraped_data.get('file_url', ''),
            embed_code=scraped_data.get('embed', ''),
            flash_enclosure_url=scraped_data.get('flash_enclosure_url', ''),
            website_url=scraped_form.cleaned_data['url'],
            thumbnail_url=scraped_form.cleaned_data.get('thumbnail_url', ''),
            openid_user=request.session.get('openid_localtv'),
            when_submitted=datetime.datetime.now())
        video.strip_description()

        video.save()

        if video.thumbnail_url:
            video.save_thumbnail()

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
    

@require_active_openid
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
        video = models.Video(
            name=embed_form.cleaned_data['name'],
            site=sitelocation.site,
            description=embed_form.cleaned_data['description'],
            embed=embed_form.cleaned_data['embed'],
            website_url=embed_form.cleaned_data.get('website_url', ''),
            thumbnail_url=embed_form.cleaned_data.get('thumbnail_url', ''),
            openid_user=request.session.get('openid_localtv'),
            when_submitted=datetime.datetime.now())

        video.save()

        if video.thumbnail_url:
            video.save_thumbnail()

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
             'scraped_form': embed_form},
            context_instance=RequestContext(request))




@require_active_openid
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
        video = models.Video(
            name=direct_form.cleaned_data['name'],
            site=sitelocation.site,
            description=direct_form.cleaned_data['description'],
            file_url=direct_form.cleaned_data['url'],
            thumbnail_url=direct_form.cleaned_data.get('thumbnail_url', ''),
            website_url=direct_form.cleaned_data.get('website_url', ''),
            openid_user=request.session.get('openid_localtv'),
            when_submitted=datetime.datetime.now())

        video.save()

        if video.thumbnail_url:
            video.save_thumbnail()

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
             'scraped_form': direct_form},
            context_instance=RequestContext(request))


@get_sitelocation
def submit_thanks(request, sitelocation=None):
    return render_to_response(
        'localtv/subsite/submit/thanks.html', {},
        context_instance=RequestContext(request))
