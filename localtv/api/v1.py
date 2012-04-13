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

from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models import Count
from tastypie import fields
from tastypie.api import Api
from tastypie.resources import ModelResource

from localtv.models import (Video, Feed, SavedSearch, Category)


class VideoResource(ModelResource):
    class Meta:
        queryset = Video.objects.filter(status=Video.ACTIVE,
                                        site=settings.SITE_ID)


class FeedResource(ModelResource):
    class Meta:
        queryset = Feed.objects.filter(status=Feed.ACTIVE,
                                       site=settings.SITE_ID)


class SearchResource(ModelResource):
    thumbnail_url = fields.CharField(blank=True, readonly=True)

    class Meta:
        queryset = SavedSearch.objects.filter(site=settings.SITE_ID)
        excludes = ('has_thumbnail', 'thumbnail_extension')

    def dehydrate_thumbnail_url(self, bundle):
        if not bundle.obj.has_thumbnail:
            thumbnail_url = None
        else:
            thumbnail_url = 'http://{netloc}{media_url}{path}'.format(
                                     netloc=Site.objects.get_current().domain,
                                     media_url=settings.MEDIA_URL,
                                     path=bundle.obj.thumbnail_path)
        return thumbnail_url


class CategoryResource(ModelResource):
    class Meta:
        queryset = Category.objects.filter(site=settings.SITE_ID)
        excludes = ('contest_mode',)


api = Api(api_name='v1')
api.register(VideoResource())
api.register(FeedResource())
api.register(SearchResource())
api.register(CategoryResource())
