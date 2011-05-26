# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
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

from django.utils.encoding import force_unicode

from haystack import indexes
from haystack import site
from localtv.models import Video, VIDEO_STATUS_ACTIVE


class VideoIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    feed = indexes.IntegerField(model_attr='feed__pk', null=True)
    search = indexes.IntegerField(model_attr='search__pk', null=True)
    user = indexes.IntegerField(model_attr='user__pk', null=True)
    tags = indexes.MultiValueField()
    categories = indexes.MultiValueField()
    authors = indexes.MultiValueField()
    playlists = indexes.MultiValueField()

    def get_queryset(self):
        """
        Custom queryset to only search approved videos.
        """
        return Video.objects.filter(status=VIDEO_STATUS_ACTIVE)

    def get_updated_field(self):
        return 'when_modified'

    def _prepare_field(self, video, field, attr='pk', normalize=int):
        return [normalize(getattr(rel, attr))
                for rel in getattr(video, field).all()]

    def prepare_tags(self, video):
        return self._prepare_field(video, 'tags', 'name', force_unicode)

    def prepare_categories(self, video):
        return self._prepare_field(video, 'categories')

    def prepare_authors(self, video):
        return self._prepare_field(video, 'authors')

    def prepare_playlists(self, video):
        return self._prepare_field(video, 'playlists')

site.register(Video, VideoIndex)
