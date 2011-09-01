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

import hashlib

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import Http404
from django.utils.translation import ugettext as _

from localtv.feeds.views import BaseVideosFeed, LOCALTV_FEED_LENGTH
from localtv import models

def generate_secret():
    sha = hashlib.sha1(settings.DATABASE_NAME)
    sha.update('admin_feed')
    sha.update(str(settings.SITE_ID))
    sha.update(settings.SECRET_KEY)
    return sha.hexdigest()[:16]

def verify_secret(func):
    def wrapper(request, secret):
        if secret != generate_secret():
            raise Http404
        return func(request)
    return wrapper

class UnapprovedVideosFeed(BaseVideosFeed):
    def link(self):
        return reverse('localtv_admin_approve_reject')

    def title(self):
        return "%s: %s" % (
            self.sitelocation.site.name, _('Videos Awaiting Moderation'))

    def _actual_items(self):
        return models.Video.objects.unapproved().filter(
            site=Site.objects.get_current()
        ).order_by(
            'when_submitted', 'when_published'
        )


class UnapprovedUserVideosFeed(UnapprovedVideosFeed):
    def title(self):
        return "%s: %s" % (
            Site.objects.get_current().name, _('Unapproved User Submissions'))

    def items(self):
        return models.Video.objects.unapproved().filter(
            site=Site.objects.get_current(),
            feed=None,
            search=None
        ).order_by(
            'when_submitted', 'when_published'
        )


unapproved = verify_secret(UnapprovedVideosFeed())
unapproved_user = verify_secret(UnapprovedUserVideosFeed())
