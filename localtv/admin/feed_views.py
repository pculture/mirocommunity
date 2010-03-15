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

try:
    import cPickle as pickle
except ImportError:
    import pickle
import datetime
import re
import sys
import os
import urllib2

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from importlib import import_module
import simplejson

from localtv.decorators import get_sitelocation, require_site_admin, \
    referrer_redirect
from localtv import models, tasks, util
from localtv.admin import forms

from vidscraper import bulk_import

VIDEO_SERVICE_TITLES = (
    re.compile(r'Uploads by (.+)'),
    re.compile(r"Vimeo / (.+)'s? uploaded videos"),
    re.compile(r'Vimeo / (.+)'),
    re.compile(r"Dailymotion - (.+)'s")
    )

@require_site_admin
@get_sitelocation
def add_feed(request, sitelocation=None):
    if request.method == 'GET':
        def gen():
            yield render_to_response('localtv/admin/feed_wait.html',
                                     {
                    'message': 'Checking out this URL',
                    'feed_url': request.GET.get('feed_url')},
                                     context_instance=RequestContext(request))
            yield add_feed_response(request, sitelocation)
        return util.HttpMixedReplaceResponse(request, gen())
    else:
        return add_feed_response(request, sitelocation)


def add_feed_response(request, sitelocation=None):
    add_form = forms.AddFeedForm(request.GET)

    if not add_form.is_valid():
        return HttpResponseBadRequest(
            add_form['feed_url'].errors.as_text())

    feed_url = add_form.cleaned_data['feed_url']
    parsed_feed = add_form.cleaned_data['parsed_feed']

    title = parsed_feed.feed.title
    for regexp in VIDEO_SERVICE_TITLES:
        match = regexp.match(title)
        if match:
            title = match.group(1)
            break

    defaults = {
        'name': title,
        'feed_url': feed_url,
        'webpage': parsed_feed.feed.get('link', ''),
        'description': parsed_feed.feed.get('summary', ''),
        'when_submitted': datetime.datetime.now(),
        'last_updated': datetime.datetime.now(),
        'status': models.FEED_STATUS_ACTIVE,
        'user': request.user,
        'etag': '',
        'auto_approve': bool(request.POST.get('auto_approve', False))}

    video_count = bulk_import.video_count(feed_url, parsed_feed)

    if request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse('localtv_admin_manage_page'))

        form = forms.SourceForm(request.POST, instance=models.Feed(**defaults))
        if form.is_valid():
            feed, created = models.Feed.objects.get_or_create(
                feed_url=defaults['feed_url'],
                site=sitelocation.site,
                defaults=defaults)

            if not created:
                for key, value in defaults.items():
                    setattr(feed, key, value)

            for key, value in form.cleaned_data.items():
                setattr(feed, key, value)

            thumbnail_url = util.get_thumbnail_url(parsed_feed.feed)
            if thumbnail_url:
                thumbnail_file = ContentFile(
                    urllib2.urlopen(thumbnail_url).read())
                feed.save_thumbnail_from_file(thumbnail_file)

            if feed.video_service():
                user, created = User.objects.get_or_create(
                    username=feed.name[:30],
                    defaults={'email': ''})
                if created:
                    user.set_unusable_password()
                    models.Profile.objects.create(
                        user=user,
                        website=defaults['webpage'])
                    user.save()
                feed.auto_authors.add(user)
            feed.save()

            return HttpResponseRedirect(reverse('localtv_admin_feed_add_done',
                                                args=[feed.pk]))

    else:
        form = forms.SourceForm(instance=models.Feed(**defaults))
    return render_to_response('localtv/admin/add_feed.html',
                              {'form': form,
                               'video_count': video_count},
                              context_instance=RequestContext(request))


@require_site_admin
@get_sitelocation
def add_feed_done(request, feed_id, sitelocation):
    feed = models.Feed.objects.get(pk=feed_id)
    if 'task_id' in request.GET:
        task_id = request.GET['task_id']
    else:
        mod = import_module(settings.SETTINGS_MODULE)
        manage_py = os.path.join(
            os.path.dirname(mod.__file__),
            'manage.py')
        result = tasks.check_call.delay((
                getattr(settings, 'PYTHON_EXECUTABLE', sys.executable),
                manage_py,
                'bulk_import',
                feed_id))
        return HttpResponseRedirect('%s?task_id=%s' % (
                request.path, result.task_id))

    cache_key = 'celery-task-meta-%s' % task_id
    result = cache.get(cache_key)
    if result is not None:
        result = pickle.loads(str(result))
        context = {'feed': feed,
                   'result': result}
        if result['status'] != 'FAILURE':
            json = simplejson.loads(result['result'])
            context.update(json)
        return render_to_response('localtv/admin/feed_done.html',
                                  context,
                                  context_instance=RequestContext(request))
    else:
        return render_to_response('localtv/admin/feed_wait.html',
                                  {'feed': feed,
                                   'task_id': task_id},
                                  context_instance=RequestContext(request))


@referrer_redirect
@require_site_admin
@get_sitelocation
def feed_auto_approve(request, feed_id, sitelocation=None):
    feed = get_object_or_404(
        models.Feed,
        id=feed_id,
        site=sitelocation.site)

    feed.auto_approve = not request.GET.get('disable')
    feed.save()

    return HttpResponse('SUCCESS')
