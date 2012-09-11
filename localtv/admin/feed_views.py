# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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
import urllib2

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.forms.models import construct_instance
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

from localtv.decorators import require_site_admin, referrer_redirect
from localtv.exceptions import CannotOpenImageUrl
from localtv import tasks, utils
from localtv.models import Feed, SiteSettings
from localtv.admin import forms

Profile = utils.get_profile_model()

VIDEO_SERVICE_TITLES = (
    re.compile(r'Uploads by (.+)'),
    re.compile(r"Vimeo / (.+)'s? uploaded videos"),
    re.compile(r'Vimeo / (.+)'),
    re.compile(r"(.+)'s videos on Vimeo"),
    re.compile(r"Videos (.+) likes on Vimeo"),
    re.compile(r"(.+) on Vimeo"),
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

    title = scraped_feed.title or ''

    for regexp in VIDEO_SERVICE_TITLES:
        match = regexp.match(title)
        if match:
            title = match.group(1)
            break
        
    defaults = {
        'name': title,
        'feed_url': feed_url,
        'webpage': scraped_feed.webpage or '',
        'description': scraped_feed.description or '',
        'etag': scraped_feed.etag or '',
        'when_submitted': datetime.datetime.now(),
        'last_updated': datetime.datetime.now(),
        'status': Feed.INACTIVE,
        'user': request.user,

        'auto_approve': bool(request.POST.get('auto_approve', False))}

    if request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse('localtv_admin_manage_page'))

        form = forms.SourceForm(request.POST, instance=Feed(**defaults))
        if form.is_valid():
            feed, created = Feed.objects.get_or_create(
                feed_url=defaults['feed_url'],
                site=SiteSettings.objects.get_current().site,
                defaults=defaults)

            if not created:
                for key, value in defaults.items():
                    setattr(feed, key, value)

            construct_instance(form, feed)

            thumbnail_url = scraped_feed.thumbnail_url

            if thumbnail_url:
                try:
                    thumbnail_file = ContentFile(
                        urllib2.urlopen(
                            utils.quote_unicode_url(thumbnail_url)).read())
                except IOError:
                    # couldn't get the thumbnail
                    pass
                else:
                    try:
                        feed.thumbnail_file = thumbnail_file
                    except CannotOpenImageUrl:
                        # couldn't parse the thumbnail. Not sure why this
                        # raises CannotOpenImageUrl, tbh.
                        pass
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

            tasks.feed_update.delay(
                feed.pk,
                using=tasks.CELERY_USING,
                clear_rejected=True)

            return HttpResponseRedirect(reverse('localtv_admin_manage_page'))

    else:
        form = forms.SourceForm(instance=Feed(**defaults))
    return render_to_response('localtv/admin/add_feed.html',
                              {'form': form,
                               'video_count': scraped_feed.video_count},
                              context_instance=RequestContext(request))

@referrer_redirect
@require_site_admin
def feed_auto_approve(request, feed_id):
    feed = get_object_or_404(
        Feed,
        id=feed_id,
        site=SiteSettings.objects.get_current().site)

    feed.auto_approve = not request.GET.get('disable')
    feed.save()

    return HttpResponse('SUCCESS')
