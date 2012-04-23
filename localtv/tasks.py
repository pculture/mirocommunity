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

import datetime
import logging
import random

from celery.exceptions import MaxRetriesExceededError
from celery.task import task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.loading import get_model
from django.contrib.auth.models import User
from haystack import connections
from haystack.query import SearchQuerySet


class DummyException(Exception):
    """
    Dummy exception; nothing raises me.
    """

try:
   from xapian import DatabaseError
except ImportError:
    DatabaseError = DummyException
try:
    from whoosh.store import LockError
except ImportError:
    LockError = DummyException


from localtv import utils
from localtv.exceptions import CannotOpenImageUrl
from localtv.models import Video, Feed, SiteSettings, SavedSearch, Category
from localtv.settings import USE_HAYSTACK
from localtv.tiers import Tier


CELERY_USING = getattr(settings, 'LOCALTV_CELERY_USING', 'default')


@task(ignore_result=True)
def update_sources(using='default'):
    feeds = Feed.objects.using(using).filter(status=Feed.ACTIVE,
                                             auto_update=True)
    for feed_pk in feeds.values_list('pk', flat=True):
        feed_update.delay(feed_pk, using=using)

    searches = SavedSearch.objects.using(using).filter(auto_update=True)
    for search_pk in searches.values_list('pk', flat=True):
        search_update.delay(search_pk, using=using)


@task(ignore_result=True)
def feed_update(feed_id, using='default', clear_rejected=False):
    try:
        feed = Feed.objects.using(using).filter(auto_update=True
                                                ).get(pk=feed_id)
    except Feed.DoesNotExist:
        logging.warn('feed_update(%s, using=%r) could not find feed',
                     feed_id, using)
        return

    feed.update(using=using, clear_rejected=clear_rejected)


@task(ignore_result=True)
def search_update(search_id, using='default'):
    try:
        search = SavedSearch.objects.using(using).filter(auto_update=True
                                                   ).get(pk=search_id)
    except SavedSearch.DoesNotExist:
        logging.warn('search_update(%s, using=%r) could not find search',
                     search_id, using)
        return
    search.update(using=using, clear_rejected=True)


@task(ignore_result=True, max_retries=None, default_retry_delay=30)
def mark_import_pending(import_app_label, import_model, import_pk,
                        using='default'):
    """
    Checks whether an import's first stage is complete. If it's not, retries
    the task with a countdown of 30.

    """
    import_class = get_model(import_app_label, import_model)
    try:
        source_import = import_class._default_manager.using(using).get(
                                                    pk=import_pk,
                                                    status=import_class.STARTED)
    except import_class.DoesNotExist:
        logging.debug('Expected %s instance (pk=%r) missing.',
                      import_class.__name__, import_pk)
        # If this is the problem, don't retry indefinitely.
        if mark_import_pending.request.retries > 10:
            raise MaxRetriesExceededError
        mark_import_pending.retry()
    source_import.last_activity = datetime.datetime.now()
    if source_import.total_videos is None:
        source_import.save()
        mark_import_pending.retry()
    # get the correct counts from the database, rather than the race-condition
    # prone count fields
    import_count = source_import.indexes.count()
    skipped_count = source_import.errors.filter(is_skip=True).count()
    if import_count != source_import.videos_imported:
        source_import.videos_imported = import_count
    if skipped_count != source_import.videos_skipped:
        source_import.videos_skipped = skipped_count
    if (source_import.videos_imported + source_import.videos_skipped
        < source_import.total_videos):
        # Then the import is incomplete. Requeue it.
        source_import.save()
        # Retry raises an exception, ending task execution.
        mark_import_pending.retry()

    # Otherwise the first stage is complete. Check whether they can take all the
    # videos.
    active_set = None
    unapproved_set = source_import.get_videos(using).filter(
        status=Video.PENDING)
    if source_import.auto_approve:
        if not SiteSettings.enforce_tiers(using=using):
            active_set = unapproved_set
            unapproved_set = None
        else:
            remaining_videos = (Tier.get(using=using).videos_limit()
                                - Video.objects.using(using
                                    ).filter(status=Video.ACTIVE
                                    ).count())
            if remaining_videos > source_import.videos_imported:
                active_set = unapproved_set
                unapproved_set = None
            elif remaining_videos > 0:
                unapproved_set = unapproved_set.order_by('when_submitted')
                # only approve `remaining_videos` videos
                when_submitted = unapproved_set[
                    remaining_videos].when_submitted
                active_set = unapproved_set.filter(
                    when_submitted__lt=when_submitted)
                unapproved_set = unapproved_set.filter(
                    when_submitted__gte=when_submitted)
    if unapproved_set is not None:
        unapproved_set.update(status=Video.UNAPPROVED)
    if active_set is not None:
        active_set.update(status=Video.ACTIVE)

    source_import.status = import_class.PENDING
    source_import.save()

    active_pks = source_import.get_videos(using).filter(
                         status=Video.ACTIVE).values_list('pk', flat=True)
    if active_pks:
        opts = Video._meta
        haystack_batch_update.delay(opts.app_label, opts.module_name,
                                    pks=list(active_pks), remove=False,
                                    using=using)

    mark_import_complete.delay(import_app_label, import_model, import_pk,
                               using=using)


@task(ignore_result=True, max_retries=None, default_retry_delay=30)
def mark_import_complete(import_app_label, import_model, import_pk,
                         using='default'):
    """
    Checks whether an import's second stage is complete. If it's not, retries
    the task with a countdown of 30.

    """
    import_class = get_model(import_app_label, import_model)
    try:
        source_import = import_class._default_manager.using(using).get(
                                                    pk=import_pk,
                                                    status=import_class.PENDING)
    except import_class.DoesNotExist:
        logging.warn('Expected %s instance (pk=%r) missing.',
                     import_class.__name__, import_pk)
        # If this is the problem, don't retry indefinitely.
        if mark_import_complete.request.retries > 10:
            raise MaxRetriesExceededError
        mark_import_complete.retry()

    if not USE_HAYSTACK:
        # No need to do any comparisons - just mark it complete.
        video_count = haystack_count = 0
        logging.debug(('mark_import_complete(%s, %s, %i, using=%s). Skipping '
                       'check because haystack is disabled.'), import_app_label,
                       import_model, import_pk, using)
    else:
        video_pks = list(source_import.get_videos(using).filter(
                                status=Video.ACTIVE).values_list('pk', flat=True))
        video_count = len(video_pks)
        if not video_pks:
            # Don't bother with the haystack query.
            haystack_count = 0
        else:
            if 'xapian' in connections[using].options['ENGINE']:
                # The pk_hack field shadows the model's pk/django_id because
                # xapian-haystack's django_id filtering is broken.
                haystack_filter = {'pk_hack__in': video_pks}
            else:
                haystack_filter = {'django_id__in': video_pks}
            haystack_count = SearchQuerySet().using(using).models(Video).filter(
               **haystack_filter).count()
        logging.debug(('mark_import_complete(%s, %s, %i, using=%s). video_count: '
                       '%i, haystack_count: %i'), import_app_label, import_model,
                       import_pk, using, video_count, haystack_count)

    if haystack_count >= video_count:
        source_import.status = import_class.COMPLETE
        if import_app_label == 'localtv' and import_model == 'feedimport':
            source_import.source.status = source_import.source.ACTIVE
            source_import.source.save()

    source_import.last_activity = datetime.datetime.now()
    source_import.save()

    if source_import.status == import_class.PENDING:
        mark_import_complete.retry()


@task(ignore_result=True, max_retries=6, default_retry_delay=10)
def video_from_vidscraper_video(vidscraper_video, site_pk,
                                import_app_label=None, import_model=None,
                                import_pk=None, status=None, author_pks=None,
                                category_pks=None, clear_rejected=False,
                                using='default'):
    import_class = get_model(import_app_label, import_model)
    try:
        source_import = import_class.objects.using(using).get(
           pk=import_pk,
           status=import_class.STARTED)
    except import_class.DoesNotExist:
        logging.warn('Retrying %r: expected %s instance (pk=%r) missing.',
                     vidscraper_video.url, import_class.__name__, import_pk)
        video_from_vidscraper_video.retry()

    try:
        try:
            vidscraper_video.load()
        except Exception:
            source_import.handle_error(
                ('Skipped %r: Could not load video data.'
                 % vidscraper_video.url),
                using=using, is_skip=True,
                with_exception=True)
            return

        if category_pks:
            categories = Category.objects.using(using).filter(pk__in=category_pks)
        else:
            categories = None

        if author_pks:
            authors = User.objects.using(using).filter(pk__in=author_pks)
        else:
            authors = None

        video = Video.from_vidscraper_video(vidscraper_video, status=status,
                                            using=using,
                                            source_import=source_import,
                                            authors=authors,
                                            categories=categories,
                                            site_pk=site_pk,
                                            commit=False,
                                            update_index=False)
        try:
            video.full_clean()
        except ValidationError, e:
            source_import.handle_error(("Skipping %r: %r" % (
                                        vidscraper_video.url, e.message_dict)),
                                        is_skip=True, using=using)
            return
        else:
            video.save(update_index=False)
            video.save_m2m()
            if clear_rejected:
                video.clear_rejected_duplicates()

            logging.debug('Made video %i: %r', video.pk, video.name)
            if video.thumbnail_url:
                video_save_thumbnail.delay(video.pk, using=using)
    except Exception:
        source_import.handle_error(('Unknown error during import of %r'
                                    % vidscraper_video.url),
                                   is_skip=True, using=using,
                                   with_exception=True)
        raise # so it shows up in the Celery log

@task(ignore_result=True)
def video_save_thumbnail(video_pk, using='default'):
    try:
        v = Video.objects.using(using).get(pk=video_pk)
    except Video.DoesNotExist:
        logging.warn(
            'video_save_thumbnail(%s, using=%r) could not find video',
            video_pk, using)
        return
    try:
        v.save_thumbnail()
    except CannotOpenImageUrl:
        try:
            return video_save_thumbnail.retry()
        except MaxRetriesExceededError:
            logging.warn(
                'video_save_thumbnail(%s, using=%r) exceeded max retries',
                video_pk, using
            )


def _haystack_database_retry(task, callback):
    """
    Tries to call ``callback``; on a haystack database access error, retries
    the task.

    """
    try:
        callback()
    except (DatabaseError, LockError), e:
        # These errors might be resolved if we just wait a bit. The wait time is
        # slightly random, with the intention of preventing LockError retries
        # from reoccurring. Maximum wait is ~30s.
        exp = min(task.request.retries, 4)
        countdown = random.random() * (2 ** exp)
        logging.debug(('%s with args %s and kwargs %s retrying due to %s '
                       'with countdown %r'), task.name, task.request.args,
                       task.request.kwargs, e.__class__.__name__, countdown)
        task.retry(countdown=countdown)


@task(ignore_result=True, max_retries=None)
def haystack_update(app_label, model_name, pks, remove=True, using='default'):
    """
    Updates the haystack records for any valid instances with the given pks.
    Generally, ``remove`` should be ``True`` so that items which are no longer
    in the ``index_queryset()`` will be taken out of the index; however,
    ``remove`` can be set to ``False`` to save some time if that behavior
    isn't needed.

    """
    model_class = get_model(app_label, model_name)
    backend = connections[using].get_backend()
    index = connections[using].get_unified_index().get_index(model_class)

    qs = index.index_queryset().using(using).filter(pk__in=pks)

    if qs:
        _haystack_database_retry(haystack_update,
                                 lambda: backend.update(index, qs))

    if remove:
        unseen_pks = set(pks) - set((instance.pk for instance in qs))
        haystack_remove.apply(args=(app_label, model_name, unseen_pks, using))


@task(ignore_result=True, max_retries=None)
def haystack_remove(app_label, model_name, pks, using='default'):
    """
    Removes the haystack records for any instances with the given pks.

    """
    model_class = get_model(app_label, model_name)
    backend = connections[using].get_backend()

    def callback():
        for pk in pks:
            backend.remove(".".join((app_label, model_name, str(pk))))

    _haystack_database_retry(haystack_remove, callback)


@task(ignore_result=True)
def haystack_batch_update(app_label, model_name, pks=None, start=None,
                          end=None, date_lookup=None, batch_size=1000,
                          remove=True, using='default'):
    """
    Batches haystack index updates for the given model. If no pks are given, a
    general reindex will be launched.

    """
    model_class = get_model(app_label, model_name)
    backend = connections[using].get_backend()
    index = connections[using].get_unified_index().get_index(model_class)

    pk_qs = index.index_queryset().using(using)
    if pks is not None:
        pk_qs = pk_qs.filter(pk__in=pks)

    if date_lookup is None:
        date_lookup = index.get_updated_field()
    if date_lookup is not None:
        if start is not None:
            pk_qs = pk_qs.filter(**{"%s__gte" % date_lookup: start})
        if end is not None:
            pk_qs = pk_qs.filter(**{"%s__lte" % date_lookup: end})

    pks = list(pk_qs.values_list('pk', flat=True))
    total = len(pks)

    for start in xrange(0, total, batch_size):
        end = min(start + batch_size, total)
        haystack_update.delay(app_label, model_name, pks[start:end],
                              remove=remove, using=using)
