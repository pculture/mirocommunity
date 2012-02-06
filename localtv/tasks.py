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

import datetime
import logging
import random

from celery.exceptions import MaxRetriesExceededError
from celery.task import task
from django.conf import settings
from django.db.models.loading import get_model
from django.contrib.auth.models import User
from haystack import site
from haystack.query import SearchQuerySet

# Some haystack backends raise lock errors if concurrent processes try to update
# the index.
try:
   from xapian import DatabaseLockError
except ImportError:
    class DatabaseLockError(Exception):
        """
        Dummy exception; nothing raises me.
        """
try:
    from whoosh.store import LockError
except ImportError:
    class LockError(Exception):
        """
        Dummy exception; nothing raises me.
        """

from localtv import utils
from localtv.exceptions import CannotOpenImageUrl
from localtv.models import Video, Feed, SiteLocation, SavedSearch, Category
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
def feed_update(feed_id, using='default'):
    try:
        feed = Feed.objects.using(using).get(pk=feed_id)
    except Feed.DoesNotExist:
        logging.warn('feed_update(%s, using=%r) could not find feed',
                     feed_id, using)
        return

    feed.update(using=using, clear_rejected=True)


@task(ignore_result=True)
def search_update(search_id, using='default'):
    try:
        search = SavedSearch.objects.using(using).get(pk=search_id)
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
        if not SiteLocation.enforce_tiers(using=using):
            active_set = unapproved_set
            unapproved_set = None
        else:
            remaining_videos = (Tier.get().videos_limit()
                                - Video.objects.using(using
                                    ).filter(status=Video.ACTIVE
                                    ).count())
            if remaining_videos > source_import.videos_imported:
                active_set = unapproved_set
                unapproved_set = None
            else:
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
        for pk in active_pks:
            haystack_update_index.delay(opts.app_label, opts.module_name,
                                        pk, is_removal=False,
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

    video_pks = list(source_import.get_videos(using).filter(
                            status=Video.ACTIVE).values_list('pk', flat=True))
    video_count = len(video_pks)
    if not video_pks:
        # Don't bother with the haystack query.
        haystack_count = 0
    else:
        if settings.HAYSTACK_SEARCH_ENGINE == 'xapian':
            # The pk_hack field shadows the model's pk/django_id because
            # xapian-haystack's django_id filtering is broken.
            haystack_filter = {'pk_hack__in': video_pks}
        else:
            haystack_filter = {'django_id__in': video_pks}
        haystack_count = SearchQuerySet().models(Video).filter(**haystack_filter
                                                      ).count()
    
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
    except import_class.DoesNotExist, e:
        logging.warn('Retrying %r: expected %s instance (pk=%r) missing.',
                     vidscraper_video.url, import_class.__name__, import_pk)
        request = video_from_vidscraper_video.request
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

        if not vidscraper_video.title:
            source_import.handle_error(
                ('Skipped %r: Failed to scrape basic data.'
                 % vidscraper_video.url),
                is_skip=True, using=using)
            return

        if ((vidscraper_video.file_url_expires or
             not vidscraper_video.file_url)
            and not vidscraper_video.embed_code):
            source_import.handle_error(('Skipping %r: no file or embed code.'
                                        % vidscraper_video.url),
                                       is_skip=True, using=using)
            return

        site_videos = Video.objects.using(using).filter(site=site_pk)

        if vidscraper_video.guid:
            guid_videos = site_videos.filter(guid=vidscraper_video.guid)
            if clear_rejected:
                guid_videos.filter(status=Video.REJECTED).delete()
            if guid_videos.exists():
                source_import.handle_error(('Skipping %r: duplicate guid.'
                                            % vidscraper_video.url),
                                           is_skip=True, using=using)
                return

        if vidscraper_video.link:
            videos_with_link = site_videos.filter(
                website_url=vidscraper_video.link)
            if clear_rejected:
                videos_with_link.filter(status=Video.REJECTED).delete()
            if videos_with_link.exists():
                source_import.handle_error(('Skipping %r: duplicate link.'
                                            % vidscraper_video.url),
                                           is_skip=True, using=using)
                return

        categories = Category.objects.using(using).filter(pk__in=category_pks)

        if author_pks:
            authors = User.objects.using(using).filter(pk__in=author_pks)
        else:
            if vidscraper_video.user:
                name = vidscraper_video.user
                if ' ' in name:
                    first, last = name.split(' ', 1)
                else:
                    first, last = name, ''
                author, created = User.objects.db_manager(using).get_or_create(
                    username=name[:30],
                    defaults={'first_name': first[:30],
                              'last_name': last[:30]})
                if created:
                    author.set_unusable_password()
                    author.save()
                    utils.get_profile_model().objects.db_manager(using).create(
                       user=author,
                       website=vidscraper_video.user_url or '')
                authors = [author]
            else:
                authors = []

        # Since we check above whether the vidscraper_video is valid, we don't
        # catch InvalidVideo here, since it would be unexpected.
        video = Video.from_vidscraper_video(vidscraper_video, status=status,
                                            using=using,
                                            source_import=source_import,
                                            authors=authors,
                                            categories=categories,
                                            site_pk=site_pk)
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
        

@task(ignore_result=True, max_retries=None)
def haystack_update_index(app_label, model_name, pk, is_removal,
                          using='default'):
    """
    Updates a haystack index for the given model (specified by ``app_label``
    and ``model_name``). If ``is_removal`` is ``True``, a fake instance is
    constructed with the given ``pk`` and passed to the index's
    :meth:`remove_object` method. Otherwise, the latest version of the instance
    is fetched from the database and passed to the index's
    :meth:`update_object` method.

    If an import_app_label, import_model, and import_pk are provided, this task
    will spawn ``mark_import_complete``.

    """
    model_class = get_model(app_label, model_name)
    search_index = site.get_index(model_class)
    try:
        if is_removal:
            instance = model_class(pk=pk)
            search_index.remove_object(instance)
        else:
            try:
                instance = Video.objects.using(using).get(pk=pk)
            except model_class.DoesNotExist:
                logging.debug(('haystack_update_index(%r, %r, %r, %r, using=%r)'
                               ' could not find video with pk %i'), app_label,
                               model_name, pk, is_removal, using, pk)
            else:
                if instance.status == Video.ACTIVE:
                    search_index.update_object(instance)
                else:
                    search_index.remove_object(instance)
    except (DatabaseLockError, LockError), e:
        # maximum wait is ~30s
        exp = min(haystack_update_index.request.retries, 4)
        countdown = random.random() * (2 ** exp)
        logging.debug(('haystack_update_index(%r, %r, %r, %r, using=%r) '
                       'retrying due to %s with countdown %r'), app_label,
                       model_name, pk, is_removal, using, e.__class__.__name__,
                       countdown)
        haystack_update_index.retry(countdown=countdown)
