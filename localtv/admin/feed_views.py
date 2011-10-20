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
import re
import sys
import os
import urllib2

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils import simplejson
from django.views.decorators.csrf import csrf_protect

import celery
from importlib import import_module

from localtv.decorators import require_site_admin, referrer_redirect
from localtv import tasks, utils
from localtv.models import Feed, SiteLocation
from localtv.admin import forms

from vidscraper.utils.feedparser import get_item_thumbnail_url

Profile = utils.get_profile_model()

VIDEO_SERVICE_TITLES = (
    re.compile(r'Uploads by (.+)'),
    re.compile(r"Vimeo / (.+)'s? uploaded videos"),
    re.compile(r'Vimeo / (.+)'),
    re.compile(r"Dailymotion - (.+)'s")
    )

@require_site_admin
@csrf_protect
def add_feed(request):
    add_form = forms.AddFeedForm(request.GET)

    if not add_form.is_valid():
        return HttpResponseBadRequest(
            add_form['feed_url'].errors.as_text())

    feed_url = add_form.cleaned_data['feed_url']
    scraped_feed = add_form.cleaned_data['scraped_feed']
    parsed_feed = add_form.cleaned_data['parsed_feed']

    if scraped_feed:
        scraped_feed.load()
        title = scraped_feed.title or ''
    else:
        title = getattr(parsed_feed.feed, 'title', '') or feed_url

    for regexp in VIDEO_SERVICE_TITLES:
        match = regexp.match(title)
        if match:
            title = match.group(1)
            break
        
    defaults = {
        'name': title,
        'feed_url': feed_url,
        'when_submitted': datetime.datetime.now(),
        'last_updated': datetime.datetime.now(),
        'status': Feed.UNAPPROVED,
        'user': request.user,

        'auto_approve': bool(request.POST.get('auto_approve', False))}

    if scraped_feed:
        defaults.update({
                'webpage': scraped_feed.webpage or '',
                'description': scraped_feed.description or '',
                'etag': scraped_feed.etag or ''
                })
        video_count = scraped_feed.entry_count
    else:
        defaults.update({
                'webpage': parsed_feed.feed.get('link', ''),
                'description': parsed_feed.feed.get('summary', ''),
                'etag': parsed_feed.get('etag', ''),
                })
        video_count = len(parsed_feed.entries)

    if request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse('localtv_admin_manage_page'))

        form = forms.SourceForm(request.POST, instance=Feed(**defaults))
        if form.is_valid():
            feed, created = Feed.objects.get_or_create(
                feed_url=defaults['feed_url'],
                site=SiteLocation.objects.get_current().site,
                defaults=defaults)

            if not created:
                for key, value in defaults.items():
                    setattr(feed, key, value)

            for key, value in form.cleaned_data.items():
                setattr(feed, key, value)

            try:
                if scraped_feed:
                    thumbnail_url = get_item_thumbnail_url(
                        scraped_feed.parsed_feed)
                else:
                    thumbnail_url = get_item_thumbnail_url(parsed_feed.feed)
            except KeyError:
                thumbnail_url = None
            if thumbnail_url:
                try:
                    thumbnail_file = ContentFile(
                        urllib2.urlopen(
                            utils.quote_unicode_url(thumbnail_url)).read())
                except IOError: # couldn't get the thumbnail
                    pass
                else:
                    feed.save_thumbnail_from_file(thumbnail_file)
            if feed.video_service():
                user, created = User.objects.get_or_create(
                    username=feed.name[:30],
                    defaults={'email': ''})
                if created:
                    user.set_unusable_password()
                    Profile.objects.create(
                        user=user,
                        website=defaults['webpage'])
                    user.save()
                feed.auto_authors.add(user)
            feed.save()

            return HttpResponseRedirect(reverse('localtv_admin_feed_add_done',
                                                args=[feed.pk]))

    else:
        form = forms.SourceForm(instance=Feed(**defaults))
    return render_to_response('localtv/admin/add_feed.html',
                              {'form': form,
                               'video_count': video_count},
                              context_instance=RequestContext(request))


@require_site_admin
def add_feed_done(request, feed_id):
    feed = get_object_or_404(Feed, pk=feed_id)
    if 'task_id' in request.GET:
        task_id = request.GET['task_id']
        task = celery.result.AsyncResult(task_id)
    else:
        mod = import_module(settings.SETTINGS_MODULE)
        manage_py = os.path.join(
            os.path.dirname(mod.__file__),
            'manage.py')
        task = tasks.check_call.delay(
            (getattr(settings, 'PYTHON_EXECUTABLE', sys.executable),
             manage_py,
             'bulk_import',
             feed_id),
            env={'DJANGO_SETTINGS_MODULE': settings.SETTINGS_MODULE})
        if not task.ready():
            return HttpResponseRedirect('%s?task_id=%s' % (
                    request.path, task.task_id))

    if task.ready(): # completed
        context = {'feed': feed,
                   'result': {
                'status': task.status,
                'result': task.result}}
        if task.successful():
            json = simplejson.loads(task.result)
            context.update(json)
        else:
            feed.status = Feed.ACTIVE
            feed.save()
            if settings.DEBUG:
                raise RuntimeError(
                    'Exception during Celery task:\n%s' % task.result)

        return render_to_response('localtv/admin/feed_done.html',
                                  context,
                                  context_instance=RequestContext(request))
    else:
        videos_that_are_fully_thumbnailed = feed.video_set.exclude(
            status=Feed.PENDING_THUMBNAIL)
        fully_thumbnailed_count = videos_that_are_fully_thumbnailed.count()
        return render_to_response(
            'localtv/admin/feed_wait.html',
            {'feed': feed,
             'fully_thumbnailed_count': fully_thumbnailed_count,
             'task_id': task_id},
            context_instance=RequestContext(request))


@referrer_redirect
@require_site_admin
def feed_auto_approve(request, feed_id):
    feed = get_object_or_404(
        Feed,
        id=feed_id,
        site=SiteLocation.objects.get_current().site)

    feed.auto_approve = not request.GET.get('disable')
    feed.save()

    return HttpResponse('SUCCESS')
