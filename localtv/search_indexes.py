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

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db.models import signals
from django.template import loader
from haystack import indexes
from haystack.query import SearchQuerySet
from tagging.models import Tag

from localtv.models import Video, Feed, SavedSearch
from localtv.playlists.models import PlaylistItem
from localtv.tasks import haystack_update, haystack_remove


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
        self._enqueue_instance(instance, haystack_update)

    def _enqueue_removal(self, instance, **kwargs):
        self._enqueue_instance(instance, haystack_remove)

    def _enqueue_instance(self, instance, task):
        self._enqueue(instance._meta.app_label,
                      instance._meta.module_name,
                      [instance.pk], task,
                      using=instance._state.db)

    def _enqueue(self, app_label, model_name, pks, task, using='default'):
        if using == 'default':
            # This gets called from both Celery and from the MC application.
            # If we're in the web app, `using` is generally 'default', so we
            # need to use CELERY_USING as our database.  If they're the same,
            # or we're not using separate databases, this is a no-op.
            using = CELERY_USING
        task.delay(app_label, model_name, pks, using=using)


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
    #: Watch count for the last week.
    watch_count = indexes.IntegerField()
    last_featured = indexes.DateTimeField(model_attr='last_featured',
                                          default=DATETIME_NULL_PLACEHOLDER)
    when_approved = indexes.DateTimeField(model_attr='when_approved',
                                          default=DATETIME_NULL_PLACEHOLDER)

    def _setup_save(self):
        super(VideoIndex, self)._setup_save()
        signals.post_save.connect(self._enqueue_related_update,
                                  sender=PlaylistItem)

    def _setup_delete(self):
        super(VideoIndex, self)._setup_save()
        signals.post_delete.connect(self._enqueue_related_delete,
                                    sender=PlaylistItem)
        for model in (Feed, Site, User, SavedSearch):
            signals.post_delete.connect(self._enqueue_fk_delete,
                                        sender=model)

    def _teardown_save(self):
        super(VideoIndex, self)._teardown_save()
        signals.post_save.disconnect(self._enqueue_related_update,
                                     sender=PlaylistItem)

    def _teardown_delete(self):
        super(VideoIndex, self)._teardown_delete()
        signals.post_delete.disconnect(self._enqueue_related_delete,
                                       sender=PlaylistItem)
        for model in (Feed, Site, User, SavedSearch):
            signals.post_delete.disconnect(self._enqueue_fk_delete,
                                           sender=model)

    def _enqueue_related_update(self, instance, **kwargs):
        self._enqueue_update(instance.video)

    def _enqueue_related_delete(self, instance, **kwargs):
        try:
            self._enqueue_update(instance.video)
        except Video.DoesNotExist:
            # We'll have picked up this delete from the Video directly, so
            # don't worry about it here.
            pass

    def _enqueue_fk_delete(self, instance, **kwargs):
        related = {
            Feed: 'feed',
            SavedSearch: 'search',
            User: 'user',
            Site: 'site',
        }
        try:
            field_name = related[instance.__class__]
        except KeyError:
            raise ValueError('Unknown related model.')
        sqs = SearchQuerySet().models(self.get_model()).filter(
                                                  **{field_name: instance.pk})
        pks = [r.pk for r in sqs]
        self._enqueue(Video._meta.app_label,
                      Video._meta.module_name,
                      pks, haystack_remove,
                      using=instance._state.db)

    def prepare(self, obj):
        """
        Disable uploadtemplate loader - it always uses the default database.
        This is a trailing necessity of the CELERY_USING hack.

        """
        if 'uploadtemplate.loader.Loader' in settings.TEMPLATE_LOADERS:
            old_template_loaders = settings.TEMPLATE_LOADERS
            loader.template_source_loaders = None
            settings.TEMPLATE_LOADERS = tuple(loader
                                     for loader in settings.TEMPLATE_LOADERS
                                     if loader != 'uploadtemplate.loader.Loader')
            super(VideoIndex, self).prepare(obj)
            loader.template_source_loaders = None
            settings.TEMPLATE_LOADERS = old_template_loaders
        else:
            super(VideoIndex, self).prepare(obj)
        return self.prepared_data

    def get_model(self):
        return Video

    def index_queryset(self):
        """
        Custom queryset to only search active videos and to annotate them
        with the watch_count.

        """
        model = self.get_model()
        return model._default_manager.filter(status=model.ACTIVE
                                  ).with_watch_count()

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
        # We manually run this process to be sure that the tags are fetched
        # from the correct database (not just "default").
        using = video._state.db
        ct = ContentType.objects.db_manager(using).get_for_model(video)
        tags = Tag.objects.using(using).filter(items__content_type__pk=ct.pk,
                                               items__object_id=video.pk)
        return [int(tag.pk) for tag in tags]

    def prepare_categories(self, video):
        return [int(rel.pk) for rel in video.all_categories]

    def prepare_authors(self, video):
        return self._prepare_rel_field(video, 'authors')

    def prepare_playlists(self, video):
        return self._prepare_rel_field(video, 'playlists')

    def prepare_watch_count(self, video):
        try:
            return video.watch_count
        except AttributeError:
            since = datetime.now() - timedelta(7)
            return video.watch_set.filter(timestamp__gt=since).count()

    def prepare_best_date(self, video):
        return video.when_approved or video.when_submitted

    def prepare_best_date_with_published(self, video):
        return video.when_published or self.prepare_best_date(video)

    def _enqueue_instance(self, instance, task):
        if (not instance.name and not instance.description
            and not instance.website_url and not instance.file_url):
            # fake instance for testing. TODO: This should probably not be done.
            return
        # This attribute can be set by passing ``update_index`` as a kwarg to
        # :meth:`Video.save`. It defaults to ``True``.
        if not getattr(instance, '_update_index', True):
            return
        super(VideoIndex, self)._enqueue_instance(instance, task)
