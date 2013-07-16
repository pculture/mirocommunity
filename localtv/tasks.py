import datetime
import httplib
import logging
import random
import urllib

from celery.task import task
from daguerre.utils import make_hash, KEEP_FORMATS, DEFAULT_FORMAT
from django.core.files.base import File
from django.core.files.temp import NamedTemporaryFile
from django.core.files.storage import default_storage
from django.db.models.loading import get_model
from haystack import connection_router, connections
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

from localtv.models import Video, Feed, SavedSearch
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
    using = connection_router.for_write()[0]
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
    using = connection_router.for_write()[0]
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
    using = connection_router.for_write()[0]
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
