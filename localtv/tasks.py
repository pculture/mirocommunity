import datetime
import httplib
import logging
import random
import urllib

from celery.exceptions import MaxRetriesExceededError
from celery.task import task
from daguerre.utils import make_hash, KEEP_FORMATS, DEFAULT_FORMAT
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.core.files.temp import NamedTemporaryFile
from django.core.files.storage import default_storage
from django.db.models import Q
from django.db.models.loading import get_model
from django.contrib.auth.models import User
from haystack import connection_router, connections
from haystack.query import SearchQuerySet
from vidscraper.videos import Video as VidscraperVideo
try:
    from PIL import Image
except ImportError:
    import Image

class DummyException(Exception):
    """
    Dummy exception; nothing raises me.
    """
try:
    from whoosh.store import LockError
except ImportError:
    LockError = DummyException

from localtv.models import Video, Feed, SavedSearch, Category
from localtv.settings import USE_HAYSTACK, API_KEYS
from localtv.signals import pre_mark_as_active
from localtv.utils import quote_unicode_url


@task(ignore_result=True)
def update_sources():
    feeds = Feed.objects.filter(status=Feed.ACTIVE,
                                auto_update=True)
    for feed_pk in feeds.values_list('pk', flat=True):
        feed_update.delay(feed_pk)

    searches = SavedSearch.objects.filter(auto_update=True)
    for search_pk in searches.values_list('pk', flat=True):
        search_update.delay(search_pk)


@task(ignore_result=True)
def feed_update(feed_id, clear_rejected=False):
    try:
        feed = Feed.objects.filter(auto_update=True
                                                ).get(pk=feed_id)
    except Feed.DoesNotExist:
        logging.warn('feed_update(%s) could not find feed',
                     feed_id)
        return

    feed.update(clear_rejected=clear_rejected)


@task(ignore_result=True)
def search_update(search_id):
    try:
        search = SavedSearch.objects.filter(auto_update=True
                                            ).get(pk=search_id)
    except SavedSearch.DoesNotExist:
        logging.warn('search_update(%s) could not find search',
                     search_id)
        return
    search.update(clear_rejected=True)


@task(ignore_result=True, max_retries=None, default_retry_delay=30)
def mark_import_pending(import_app_label, import_model, import_pk):
    """
    Checks whether an import's first stage is complete. If it's not, retries
    the task with a countdown of 30.

    """
    import_class = get_model(import_app_label, import_model)
    try:
        source_import = import_class._default_manager.get(
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

    # Otherwise the first stage is complete. Check whether they can take all
    # the videos.
    if source_import.auto_approve:
        active_set = source_import.get_videos().filter(
            status=Video.PENDING)

        for receiver, response in pre_mark_as_active.send_robust(
            sender=source_import,
            active_set=active_set):
            if response:
                if isinstance(response, Q):
                    active_set = active_set.filter(response)
                elif isinstance(response, dict):
                    active_set = active_set.filter(**response)

        active_set.update(status=Video.ACTIVE)

    source_import.get_videos().filter(status=Video.PENDING).update(
        status=Video.UNAPPROVED)

    source_import.status = import_class.PENDING
    source_import.save()

    active_pks = source_import.get_videos().filter(
                         status=Video.ACTIVE).values_list('pk', flat=True)
    if active_pks:
        opts = Video._meta
        haystack_batch_update.delay(opts.app_label, opts.module_name,
                                    pks=list(active_pks), remove=False)

    mark_import_complete.delay(import_app_label, import_model, import_pk)


@task(ignore_result=True, max_retries=None, default_retry_delay=30)
def mark_import_complete(import_app_label, import_model, import_pk):
    """
    Checks whether an import's second stage is complete. If it's not, retries
    the task with a countdown of 30.

    """
    import_class = get_model(import_app_label, import_model)
    try:
        source_import = import_class._default_manager.get(
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
        logging.debug(('mark_import_complete(%s, %s, %i). Skipping '
                       'check because haystack is disabled.'), import_app_label,
                       import_model, import_pk)
    else:
        video_pks = list(source_import.get_videos().filter(
                                status=Video.ACTIVE).values_list('pk', flat=True))
        video_count = len(video_pks)
        if not video_pks:
            # Don't bother with the haystack query.
            haystack_count = 0
        else:
            haystack_filter = {'django_id__in': video_pks}
            haystack_count = SearchQuerySet().models(Video).filter(
               **haystack_filter).count()
        logging.debug(('mark_import_complete(%s, %s, %i). video_count: '
                       '%i, haystack_count: %i'), import_app_label, import_model,
                       import_pk, video_count, haystack_count)

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
def video_from_vidscraper_video(video_dict, site_pk,
                                import_app_label=None, import_model=None,
                                import_pk=None, status=None, author_pks=None,
                                category_pks=None, clear_rejected=False):
    vidscraper_video = VidscraperVideo.deserialize(video_dict, API_KEYS)
    import_class = get_model(import_app_label, import_model)
    try:
        source_import = import_class.objects.get(
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
                is_skip=True, with_exception=True)
            return

        if category_pks:
            categories = Category.objects.filter(pk__in=category_pks)
        else:
            categories = None

        if author_pks:
            authors = User.objects.filter(pk__in=author_pks)
        else:
            authors = None

        video = Video.from_vidscraper_video(vidscraper_video, status=status,
                                            source_import=source_import,
                                            authors=authors,
                                            categories=categories,
                                            site_pk=site_pk,
                                            commit=False,
                                            update_index=False)
        try:
            video.clean_fields()
            # If clear_rejected is True, we've already deleted any rejected
            # videos, so there's no need to explicitly exclude them.
            # If clear_rejected is False, this is not the first run, and
            # so rejected videos need to not be excluded in this check.
            video._check_for_duplicates(exclude_rejected=False)
            video.validate_unique()
        except ValidationError, e:
            source_import.handle_error(("Skipping %r: %r" % (
                                        vidscraper_video.url, e.message)),
                                       is_skip=True)
            return
        else:
            video.save(update_index=False)
            try:
                video.save_m2m()
            except Exception:
                video.delete()
                raise
            if clear_rejected:
                video.clear_rejected_duplicates()

            logging.debug('Made video %i: %r', video.pk, video.name)
            if video.thumbnail_url:
                video_save_thumbnail.delay(video.pk)
    except Exception:
        source_import.handle_error(('Unknown error during import of %r'
                                    % vidscraper_video.url),
                                   is_skip=True, with_exception=True)
        raise # so it shows up in the Celery log

@task(ignore_result=True)
def video_save_thumbnail(video_pk):
    try:
        video = Video.objects.get(pk=video_pk)
    except Video.DoesNotExist:
        logging.warn(
            'video_save_thumbnail(%s) could not find video',
            video_pk)
        return

    if not video.thumbnail_url:
        return

    thumbnail_url = quote_unicode_url(video.thumbnail_url)

    try:
        remote_file = urllib.urlopen(thumbnail_url)
    except httplib.InvalidURL:
        # If the URL isn't valid, erase it.
        Video.objects.filter(pk=video.pk
                    ).update(thumbnail_url='')
        return

    if remote_file.getcode() != 200:
        logging.info("Code %i when getting %r, retrying",
                     remote_file.getcode(), video.thumbnail_url)
        video_save_thumbnail.retry()

    temp = NamedTemporaryFile()
    try:
        temp.write(remote_file.read())
    except IOError:
        # Could be a temporary disruption - try again later if this was
        # a task. Otherwise reraise.
        if video_save_thumbnail.request.called_directly:
            raise
        video_save_thumbnail.retry()

    temp.seek(0)
    try:
        im = Image.open(temp)
        im.verify()
    except Exception:
        # If the file isn't valid, erase the url.
        Video.objects.filter(pk=video.pk
                    ).update(thumbnail_url='')
        return

    f = video._meta.get_field('thumbnail')
    format = im.format if im.format in KEEP_FORMATS else DEFAULT_FORMAT
    args = (video.thumbnail_url, video.pk, datetime.datetime.now().isoformat())
    filename = '.'.join((make_hash(*args, step=2), format.lower()))
    storage_path = f.generate_filename(video, filename)

    # We save the thumbnail file and then update the path on the instance
    # to avoid overwriting other changes that might have happened
    # simultaneously.
    final_path = default_storage.save(storage_path, File(temp))
    Video.objects.filter(pk=video.pk
                ).update(thumbnail=final_path)
    remote_file.close()
    temp.close()


def _haystack_database_retry(task, callback):
    """
    Tries to call ``callback``; on a haystack database access error, retries
    the task.

    """
    try:
        callback()
    except LockError, e:
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
def haystack_update(app_label, model_name, pks, remove=True):
    """
    Updates the haystack records for any valid instances with the given pks.
    Generally, ``remove`` should be ``True`` so that items which are no longer
    in the ``index_queryset()`` will be taken out of the index; however,
    ``remove`` can be set to ``False`` to save some time if that behavior
    isn't needed.

    """
    model_class = get_model(app_label, model_name)
    using = connection_router.for_write()
    backend = connections[using].get_backend()
    index = connections[using].get_unified_index().get_index(model_class)

    qs = index.index_queryset().filter(pk__in=pks)

    if qs:
        _haystack_database_retry(haystack_update,
                                 lambda: backend.update(index, qs))

    if remove:
        unseen_pks = set(pks) - set((instance.pk for instance in qs))
        haystack_remove.apply(args=(app_label, model_name, unseen_pks))


@task(ignore_result=True, max_retries=None)
def haystack_remove(app_label, model_name, pks):
    """
    Removes the haystack records for any instances with the given pks.

    """
    using = connection_router.for_write()
    backend = connections[using].get_backend()

    def callback():
        for pk in pks:
            backend.remove(".".join((app_label, model_name, str(pk))))

    _haystack_database_retry(haystack_remove, callback)


@task(ignore_result=True)
def haystack_batch_update(app_label, model_name, pks=None, start=None,
                          end=None, date_lookup=None, batch_size=100,
                          remove=True):
    """
    Batches haystack index updates for the given model. If no pks are given, a
    general reindex will be launched.

    """
    model_class = get_model(app_label, model_name)
    using = connection_router.for_write()
    index = connections[using].get_unified_index().get_index(model_class)

    pk_qs = index.index_queryset()
    if pks is not None:
        pk_qs = pk_qs.filter(pk__in=pks)

    if date_lookup is None:
        date_lookup = index.get_updated_field()
    if date_lookup is not None:
        if start is not None:
            pk_qs = pk_qs.filter(**{"%s__gte" % date_lookup: start})
        if end is not None:
            pk_qs = pk_qs.filter(**{"%s__lte" % date_lookup: end})

    pks = list(pk_qs.distinct().values_list('pk', flat=True))
    total = len(pks)

    for start in xrange(0, total, batch_size):
        end = min(start + batch_size, total)
        haystack_update.delay(app_label, model_name, pks[start:end],
                              remove=remove)
