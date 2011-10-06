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

from django.db.models import Count
from django.utils.encoding import force_unicode

from haystack import indexes
from haystack import site
from localtv.models import Video
from localtv.search.utils import SortFilterMixin


class VideoIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)

    # ForeignKey relationships
    feed = indexes.IntegerField(model_attr='feed_id', null=True)
    search = indexes.IntegerField(model_attr='search_id', null=True)
    user = indexes.IntegerField(model_attr='user_id', null=True)
    site = indexes.IntegerField(model_attr='site_id')

    # M2M relationships
    tags = indexes.MultiValueField()
    categories = indexes.MultiValueField()
    authors = indexes.MultiValueField()
    playlists = indexes.MultiValueField()

    # Aggregated/collated data.
    best_date = indexes.DateTimeField(model_attr='when')
    #: watch_count is set during :meth:`~VideoIndex.index_queryset`.
    watch_count = indexes.IntegerField(model_attr='watch_count')
    last_featured = indexes.DateTimeField(model_attr='last_featured',
                            default=SortFilterMixin._empty_value['featured'])
    when_approved = indexes.DateTimeField(model_attr='when_approved',
                            default=SortFilterMixin._empty_value['approved'])

    def index_queryset(self):
        """
        Custom queryset to only search active videos and to annotate them
        with the watch_count.

        """
        return self.model._default_manager.active().annotate(
                                                    watch_count=Count('watch'))

    def read_queryset(self):
        """
        Adds a select_related call to the normal :meth:`.index_queryset`; the
        related items only need to be in the index by id, but on read we will
        probably need more.

        """
        return self.index_queryset().select_related('feed', 'user', 'search')

    def get_updated_field(self):
        return 'when_modified'

    def _prepare_field(self, video, field):
        return [int(rel.pk) for rel in getattr(video, field).all()]

    def prepare_tags(self, video):
        return self._prepare_field(video, 'tags')

    def prepare_categories(self, video):
        return self._prepare_field(video, 'categories')

    def prepare_authors(self, video):
        return self._prepare_field(video, 'authors')

    def prepare_playlists(self, video):
        return self._prepare_field(video, 'playlists')

site.register(Video, VideoIndex)
