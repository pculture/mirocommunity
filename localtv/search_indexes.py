from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models import signals
from haystack import indexes
from haystack.query import SearchQuerySet

from localtv.models import Video, Feed, SavedSearch
from localtv.playlists.models import PlaylistItem
from localtv.tasks import haystack_update, haystack_remove


#: We use a placeholder value because support for filtering on null values is
#: lacking. We use January 1st, 1900 because Whoosh doesn't support datetime
#: values earlier than that, but we want to keep the videos with no value
#: sorted last. This should be fine since we're not dealing with youtube
#: videos uploaded in 1899.
DATETIME_NULL_PLACEHOLDER = datetime(1900, 1, 1)


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
        task.delay(instance._meta.app_label,
                   instance._meta.module_name,
                   [instance.pk])


class VideoIndex(QueuedSearchIndex, indexes.Indexable):
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
        haystack_remove.delay(Video._meta.app_label,
                              Video._meta.module_name,
                              pks)

    def get_model(self):
        return Video

    def index_queryset(self, using=None):
        """
        Custom queryset to only search active videos and to annotate them
        with the watch_count.

        """
        model = self.get_model()
        return model._default_manager.using(using).filter(status=model.PUBLISHED)

    def read_queryset(self):
        """
        Returns active videos and selects related feeds, users, and searches.

        """
        model = self.get_model()
        return model._default_manager.filter(status=model.PUBLISHED
                                    ).select_related('feed', 'user', 'search'
                                    ).prefetch_related('authors')

    def get_updated_field(self):
        return 'when_modified'

    def _prepare_rel_field(self, video, field):
        return [int(rel.pk) for rel in getattr(video, field).all()]

    def prepare_tags(self, video):
        return [int(tag.pk) for tag in video.tags]

    def prepare_categories(self, video):
        return [int(rel.pk) for rel in video.all_categories]

    def prepare_authors(self, video):
        return self._prepare_rel_field(video, 'authors')

    def prepare_playlists(self, video):
        return self._prepare_rel_field(video, 'playlists')

    def prepare_watch_count(self, video):
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
