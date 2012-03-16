# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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

from datetime import datetime

from django.db.models import Count, signals

from haystack import indexes
from localtv.models import Video, Watch
from localtv.playlists.models import PlaylistItem
from localtv.tasks import haystack_update_index

from django.conf import settings


CELERY_USING = getattr(settings, 'LOCALTV_CELERY_USING', 'default')

#: We use a placeholder value because support for filtering on null values is
#: lacking. We use ``datetime.max`` rather than ``datetime.min`` because whoosh
#: doesn't support datetime values before 1900.
DATETIME_NULL_PLACEHOLDER = datetime.max


class QueuedSearchIndex(indexes.SearchIndex):
    def _setup_save(self):
        signals.post_save.connect(self._enqueue_update,
                                    sender=self.get_model())

    def _setup_delete(self):
        signals.post_delete.connect(self._enqueue_removal,
                                    sender=self.get_model())

    def _teardown_save(self):
        signals.post_save.disconnect(self._enqueue_update,
                                    sender=self.get_model())

    def _teardown_delete(self):
        signals.post_delete.connect(self._enqueue_removal,
                                    sender=self.get_model())

    def _enqueue_update(self, instance, **kwargs):
        self._enqueue_instance(instance, False)

    def _enqueue_removal(self, instance, **kwargs):
        self._enqueue_instance(instance, True)

    def _enqueue_instance(self, instance, is_removal):
        # This attribute can be set by passing ``update_index`` as a kwarg to
        # :meth:`Video.save`. It defaults to ``True``.
        if not getattr(instance, '_update_index', True):
            return
        using = instance._state.db
        if using == 'default':
            # This gets called from both Celery and from the MC application.
            # If we're in the web app, `using` is generally 'default', so we
            # need to use CELERY_USING as our database.  If they're the same,
            # or we're not using separate databases, this is a no-op.
            using = CELERY_USING
        haystack_update_index.delay(instance._meta.app_label,
                                    instance._meta.module_name,
                                    [instance.pk],
                                    is_removal,
                                    using=using)


class VideoIndex(QueuedSearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    # HACK because xapian-haystack django_id/pk filtering is broken.
    pk_hack = indexes.IntegerField(model_attr='pk')

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
    #: The best_date field if the publish date is not considered.
    best_date = indexes.DateTimeField()
    #: The best_date field if the original date is considered.
    best_date_with_published = indexes.DateTimeField()
    watch_count = indexes.IntegerField()
    last_featured = indexes.DateTimeField(model_attr='last_featured',
                                          default=DATETIME_NULL_PLACEHOLDER)
    when_approved = indexes.DateTimeField(model_attr='when_approved',
                                          default=DATETIME_NULL_PLACEHOLDER)

    def _setup_save(self):
        super(VideoIndex, self)._setup_save()
        signals.post_save.connect(self._enqueue_related_update,
                                  sender=Watch)
        signals.post_save.connect(self._enqueue_related_update,
                                  sender=PlaylistItem)

    def _setup_delete(self):
        super(VideoIndex, self)._setup_save()
        signals.post_delete.connect(self._enqueue_related_delete,
                                    sender=PlaylistItem)

    def _teardown_save(self):
        super(VideoIndex, self)._teardown_save()
        signals.post_save.disconnect(self._enqueue_related_update,
                                     sender=Watch)
        signals.post_save.disconnect(self._enqueue_related_update,
                                     sender=PlaylistItem)

    def _teardown_delete(self):
        super(VideoIndex, self)._teardown_delete()
        signals.post_delete.disconnect(self._enqueue_related_delete,
                                       sender=PlaylistItem)

    def _enqueue_related_update(self, instance, **kwargs):
        self._enqueue_instance(instance.video, False)

    def _enqueue_related_delete(self, instance, **kwargs):
        try:
            self._enqueue_instance(instance.video, False)
        except Video.DoesNotExist:
            # We'll have picked up this delete from the Video directly, so
            # don't worry about it here.
            pass

    def get_model(self):
        return Video

    def index_queryset(self):
        """
        Custom queryset to only search active videos and to annotate them
        with the watch_count.

        """
        model = self.get_model()
        return model._default_manager.filter(status=model.ACTIVE
                                  ).annotate(watch_count=Count('watch'))

    def read_queryset(self):
        """
        Returns active videos and selects related feeds, users, and searches.

        """
        model = self.get_model()
        return model._default_manager.filter(status=model.ACTIVE
                                    ).select_related('feed', 'user', 'search')

    def get_updated_field(self):
        return 'when_modified'

    def _prepare_rel_field(self, video, field):
        return [int(rel.pk) for rel in getattr(video, field).all()]

    def prepare_tags(self, video):
        return self._prepare_rel_field(video, 'tags')

    def prepare_categories(self, video):
        return [int(rel.pk) for rel in video.all_categories]

    def prepare_authors(self, video):
        return self._prepare_rel_field(video, 'authors')

    def prepare_playlists(self, video):
        return self._prepare_rel_field(video, 'playlists')

    def prepare_watch_count(self, video):
        # video.watch_count is set during :meth:`~VideoIndex.index_queryset`.
        # If for some reason that isn't available, do a manual count.
        try:
            return video.watch_count
        except AttributeError:
            return video.watch_set.count()

    def prepare_best_date(self, video):
        return video.when_approved or video.when_submitted

    def prepare_best_date_with_published(self, video):
        return video.when_published or self.prepare_best_date(video)

    def _enqueue_instance(self, instance, is_removal):
        if (not instance.name and not instance.description
            and not instance.website_url and not instance.file_url):
            # fake instance for testing. TODO: This should probably not be done.
            return
        super(VideoIndex, self)._enqueue_instance(instance, is_removal)
