from os import path
import urlparse

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
import vidscraper

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
            'localtv/subsite/submit_video.html',
            {'sitelocation': sitelocation,
             'submit_video_form': submit_form},
            context_instance=RequestContext(request))
    else:
        submit_form = forms.SubmitVideoForm(request.POST)
        if submit_form.is_valid():
            url_filename = path.split(
                urlparse.urlsplit(
                    submit_form.cleaned_data['url'])[2])[-1]
            # try and
            try:
                scraped_data = vidscraper.auto_scrape(
                    submit_form.cleaned_data['url'])
            except vidscraper.errors.Error:
                scraped_data = None

            if scraped_data and (scraped_data.get('embed') or scraped_data.get('file_url')):
                scraped_form = forms.ScrapedSubmitVideoForm()
                scraped_form.initial['embed'] = scraped_data.get('embed')
                scraped_form.initial['website_url'] = submit_form.cleaned_data['url']
                scraped_form.initial['url'] = scraped_data.get('file_url')
                scraped_form.initial['name'] = scraped_data.get('title')
                scraped_form.initial['description'] = scraped_data.get('description')

                return render_to_response(
                    'localtv/subsite/scraped_submit_video.html',
                    {'sitelocation': sitelocation,
                     'submit_form': submit_form},
                    context_instance=RequestContext(request))

            # otherwise if it looks like a video file
            elif util.is_video_filename(url_filename):
                return render_to_response(
                    'localtv/subsite/scraped_submit_video.html',
                    {'sitelocation': sitelocation,
                     'submit_form': submit_form},
                    context_instance=RequestContext(request))
            else:
                pass
            
        else:
            return render_to_response(
                'localtv/subsite/submit_video.html',
                {'sitelocation': sitelocation,
                 'submit_form': submit_form},
                context_instance=RequestContext(request))



@require_active_openid
@get_sitelocation
def scraped_submit_video(request, sitelocation=None):
    # scrape the video again for good measure :P
    pass


@require_active_openid
@get_sitelocation
def embedrequest_submit_video(request, sitelocation=None):
    pass


@require_active_openid
@get_sitelocation
def directlink_submit_video(request, sitelocation=None):
    pass

@require_active_openid
@get_sitelocation
def preview_before_submit(request, sitelocation=None):
    submit_video_form = forms.SubmitVideoForm(request.GET)
    if not submit_video_form.is_valid():
        return HttpResponse('invalid data to form a preview')

    return render_to_response(
        'localtv/subsite/view_video.html',
        {'sitelocation': sitelocation,
         'current_video': submit_video_form.cleaned_data},
        context_instance=RequestContext(request))
