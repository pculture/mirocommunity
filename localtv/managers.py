import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models


EMPTY = object()


class SiteRelatedManager(models.Manager):
    """
    Returns an object related to a site. That object will be cached heavily
    according to the site id and database. If the object does not exist, it
    will be created.

    """
    def __init__(self):
        super(SiteRelatedManager, self).__init__()
        self._cache = {}

    def get_cached(self, site, using):
        # Make sure we're dealing with a primary key.
        if isinstance(site, Site):
            site = site.pk
        site_pk = int(site)
        if (using, site_pk) not in self._cache:
            try:
                instance = self.select_related().get(site=site_pk)
            except self.model.DoesNotExist:
                try:
                    site = Site.objects.using(using).get(pk=site_pk)
                except Site.DoesNotExist:
                    raise self.model.DoesNotExist
                instance = self._new_entry(site, using)
            self._cache[(using, site_pk)] = instance

        return self._cache[(using, site_pk)]

    def _new_entry(self, site, using):
        """Creates and returns a new entry for the cache."""
        return self.db_manager(using).create(site=site)

    def get_current(self):
        """
        Shortcut for getting the currently-active instance from the cache.

        """
        site = settings.SITE_ID
        using = self._db if self._db is not None else 'default'
        return self.get_cached(site, using)

    def clear_cache(self):
        self._cache = {}

    def _post_save(self, sender, instance, created, raw, using, **kwargs):
        self._cache[(using, instance.site_id)] = instance

    def contribute_to_class(self, model, name):
        # In addition to the normal contributions, we also attach a post-save
        # listener to cache newly-saved instances immediately. This is
        # post-save to make sure that we don't cache anything invalid.
        super(SiteRelatedManager, self).contribute_to_class(model, name)
        if not model._meta.abstract:
            models.signals.post_save.connect(self._post_save, sender=model)


class VideoQuerySet(models.query.QuerySet):

    def with_best_date(self, use_original_date=True):
        if use_original_date:
            published = 'localtv_video.when_published,'
        else:
            published = ''
        return self.extra(select={'best_date': """
COALESCE(%slocaltv_video.when_approved,
localtv_video.when_submitted)""" % published})

    def _popular_q(self, since=EMPTY):
        if since is EMPTY:
            since = datetime.datetime.now() - datetime.timedelta(days=7)

        return models.Q(watch__timestamp__gte=since)

    def popular(self, since=EMPTY):
        """
        Returns a QuerySet of videos which have been watched since ``since``,
        sorted by the number of watches since then.

        """
        return self.filter(self._popular_q(since)
                  ).distinct().annotate(watch_count=models.Count('watch')
                  ).order_by('-watch_count')

    def not_popular(self, since=EMPTY):
        """
        Returns a QuerySet of videos which have not been watched since
        ``since``.

        """
        return self.filter(~self._popular_q(since)).distinct()


class VideoManager(models.Manager):

    def get_query_set(self):
        return VideoQuerySet(self.model, using=self._db)

    def with_best_date(self, *args, **kwargs):
        return self.get_query_set().with_best_date(*args, **kwargs)

    def popular_since(self, *args, **kwargs):
        return self.get_query_set().popular_since(*args, **kwargs)

    def get_site_settings_videos(self, site_settings=None):
        """
        Returns a QuerySet of videos which are active and tied to the
        site_settings. This QuerySet is cached on the request.
        
        """
        if site_settings is None:
            from localtv.models import SiteSettings
            site_settings = SiteSettings.objects.get_current()
        return self.filter(status=self.model.PUBLISHED, site=site_settings.site)

    def get_featured_videos(self, site_settings=None):
        """
        Returns a ``QuerySet`` of active videos which are considered "featured"
        for the site_settings.

        """
        return self.get_site_settings_videos(site_settings).filter(
            last_featured__isnull=False
        ).order_by(
            '-last_featured',
            '-when_approved',
            '-when_published',
            '-when_submitted'
        )

    def get_latest_videos(self, site_settings=None):
        """
        Returns a ``QuerySet`` of active videos for the site_settings, ordered by
        decreasing ``best_date``.
        
        """
        if site_settings is None:
            from localtv.models import SiteSettings
            site_settings = SiteSettings.objects.get_current()
        return self.get_site_settings_videos(site_settings).with_best_date(
            site_settings.use_original_date
        ).order_by('-best_date')

    def get_popular_videos(self, site_settings=None):
        """
        Returns a ``QuerySet`` of active videos considered "popular" for the
        current site_settings.

        """
        from localtv.search.utils import PopularSort
        return PopularSort().sort(self.get_latest_videos(site_settings))

    def get_category_videos(self, category, site_settings=None):
        """
        Returns a ``QuerySet`` of active videos considered part of the selected
        category or its descendants for the site_settings.

        """
        if site_settings is None:
            from localtv.models import SiteSettings
            site_settings = SiteSettings.objects.get_current()
        # category.approved_set already checks active().
        return category.approved_set.filter(
            site=site_settings.site
        ).with_best_date(
            site_settings.use_original_date
        ).order_by('-best_date')

    def get_tag_videos(self, tag, site_settings=None):
        """
        Returns a ``QuerySet`` of active videos with the given tag for the
        site_settings.

        """
        if site_settings is None:
            site = settings.SITE_ID
        else:
            site = site_settings.site
        return self.model.tagged.with_all(tag).filter(status=self.model.PUBLISHED,
                                                      site=site
                                             ).order_by('-when_approved',
                                                        '-when_published',
                                                        '-when_submitted')

    def get_author_videos(self, author, site_settings=None):
        """
        Returns a ``QuerySet`` of active videos published or produced by
        ``author`` related to the site_settings.

        """
        return self.get_latest_videos(site_settings).filter(
            models.Q(authors=author) | models.Q(user=author)
        ).distinct().order_by('-best_date')

    def in_feed_order(self, feed=None, site_settings=None):
        """
        Returns a ``QuerySet`` of active videos ordered by the order they were
        in when originally imported.
        """
        if site_settings is None and feed:
            from localtv.models import SiteSettings
            site_settings = SiteSettings.objects.get_cached(site=feed.site,
                                                         using=feed._state.db)
        if site_settings:
            qs = self.get_latest_videos(site_settings)
        else:
            qs = self.all()
        if feed:
            qs = qs.filter(feed=feed)
        return qs.order_by('-feedimportindex__source_import__start',
                           'feedimportindex__index',
                           '-id')
