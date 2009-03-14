import datetime
from os import path
import urlparse

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv import models
from localtv.decorators import get_sitelocation, require_active_openid
from localtv.subsite.submit_video import forms
from localtv import util


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

            if scraped_data and (
                    scraped_data.get('embed') or scraped_data.get('file_url')):
                scraped_form = forms.ScrapedSubmitVideoForm()
                scraped_form.initial['embed'] = scraped_data.get('embed')
                scraped_form.initial['website_url'] = \
                    submit_form.cleaned_data['url']
                scraped_form.initial['file_url'] = scraped_data.get('file_url')
                scraped_form.initial['name'] = scraped_data.get('title')
                scraped_form.initial['description'] = scraped_data.get(
                    'description')
                if submit_form.cleaned_data.get('tags'):
                    scraped_form.initial['tags'] = u', '.join(
                        submit_form.cleaned_data['tags'])

                return render_to_response(
                    'localtv/subsite/submit/scraped_submit_video.html',
                    {'sitelocation': sitelocation,
                     'scraped_form': scraped_form},
                    context_instance=RequestContext(request))

            # otherwise if it looks like a video file
            elif util.is_video_filename(url_filename):
                return render_to_response(
                    'localtv/subsite/submit/embed_submit_video.html',
                    {'sitelocation': sitelocation,
                     'submit_form': submit_form},
                    context_instance=RequestContext(request))
            else:
                pass
            
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
        return HttpResponseRedirect(reverse('localtv_submit_video'))

    scraped_form = forms.ScrapedSubmitVideoForm(request.POST)
    if scraped_form.is_valid():
        # TODO: reject and warn if a video already exists

        video = models.Video(
            name=scraped_form.cleaned_data['name'],
            site=sitelocation.site,
            description=scraped_form.cleaned_data['description'],
            file_url=scraped_form.cleaned_data.get('file_url', ''),
            #embed=scraped_form.cleaned_data.get('embed'),
            website_url=scraped_form.cleaned_data['website_url'],
            when_submitted=datetime.datetime.now())

        video.save()
        tags = util.get_or_create_tags(scraped_form.cleaned_data.get('tags', []))
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
    pass


@require_active_openid
@get_sitelocation
def directlink_submit_video(request, sitelocation=None):
    pass


@get_sitelocation
def submit_thanks(request, sitelocation=None):
    return render_to_response(
        'localtv/subsite/submit/thanks.html', {},
        context_instance=RequestContext(request))
