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

from localtv import models
def update_feeds(verbose=False):
    for feed in models.Feed.objects.filter(status=models.FEED_STATUS_ACTIVE):
        feed.update_items()


def update_saved_searches(verbose=False):
    for saved_search in models.SavedSearch.objects.all():
        saved_search.update_items()


def update_publish_date(verbose=False):
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
