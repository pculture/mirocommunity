# Copyright 2009-2010 - Participatory Culture Foundation
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

from django.core.files.storage import default_storage
from django.contrib.auth.models import User

from localtv import models

TWO_MONTHS = datetime.timedelta(days=62)

def site_too_old():
    if User.objects.order_by('-last_login').values_list(
        'last_login', flat=True)[0] + TWO_MONTHS < datetime.now():
        return True
    else:
        return False


def update_feeds(verbose=False):
    if site_too_old():
        return
    for feed in models.Feed.objects.filter(status=models.FEED_STATUS_ACTIVE):
        feed.update_items()


def update_saved_searches(verbose=False):
    if site_too_old():
        return
    for saved_search in models.SavedSearch.objects.all():
        saved_search.update_items()


def update_publish_date(verbose=False):
    if site_too_old():
        return
    import vidscraper
    for v in models.Video.objects.filter(when_published__isnull=True):
        try:
            d = vidscraper.auto_scrape(v.website_url, fields=['publish_date'])
        except:
            pass
        else:
            if d:
                v.when_published = d['publish_date']
                v.save()

def update_thumbnails(verbose=False):
    if site_too_old():
        return
    for v in models.Video.objects.filter(has_thumbnail=True):
        path = v.get_original_thumb_storage_path()
        if not default_storage.exists(path):
            try:
                # resave the thumbnail
                v.save_thumbnail()
            except Exception:
                import traceback
                traceback.print_exc()

