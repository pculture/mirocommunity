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

#import eventlet
#eventlet.monkey_patch()

import datetime
import os
import itertools
import logging

import vidscraper

from celery.exceptions import MaxRetriesExceededError
from celery.task import task
from django.conf import settings
from django.db.models.loading import get_model
from django.contrib.auth.models import User
from haystack import site

from localtv import utils
from localtv.exceptions import CannotOpenImageUrl
from localtv.models import Video, Feed, SiteLocation, SavedSearch, Category
from localtv.tiers import Tier


CELERY_USING = getattr(settings, 'LOCALTV_CELERY_USING', 'default')


if hasattr(settings.DATABASES, 'module'):
    def patch_settings(func):
        def wrapper(*args, **kwargs):
            using = kwargs.get('using', None)
            if using in (None, 'default', CELERY_USING):
                logging.info('running %s(*%s, **%s) on default',
                             func, args, kwargs)
                kwargs['using'] = 'default'
                return func(*args, **kwargs)
            logging.info('running %s(*%s, **%s) on %s',
                         func, args, kwargs, using)
            environ = os.environ.copy()
            wrapped = settings._wrapped
            os.environ['DJANGO_SETTINGS_MODULE'] = '%s.settings' % using
            new_settings = settings.DATABASES.module(using)
            new_settings.DATABASES = settings.DATABASES
            settings._wrapped = new_settings
            try:
                return func(*args, **kwargs)
            finally:
                settings._wrapped = wrapped
                os.environ = environ
        wrapper.func_name = func.func_name
        wrapper.func_doc = func.func_doc
        wrapper.func_defaults = func.func_defaults
        return wrapper
else:
    def patch_settings(func):
        return func # noop

@task(ignore_result=True)
@patch_settings
def update_sources(using='default'):
    feeds = Feed.objects.using(using).filter(status=Feed.ACTIVE,
                                             auto_update=True)
    for feed_pk in feeds.values_list('pk', flat=True):
        feed_update.delay(feed_pk, using=using)

    searches = SavedSearch.objects.using(using).filter(auto_update=True)
    for search_pk in searches.values_list('pk', flat=True):
        search_update.delay(search_pk, using=using)

@task(ignore_result=True)
@patch_settings
def feed_update(feed_id, using='default'):
    try:
        feed = Feed.objects.using(using).get(pk=feed_id)
    except Feed.DoesNotExist:
        logging.warn('feed_update(%s, using=%r) could not find feed',
                     feed_id, using)
        return

    feed.update(using=using, clear_rejected=True)

@task(ignore_result=True)
@patch_settings
def search_update(search_id, using='default'):
    try:
        search = SavedSearch.objects.using(using).get(pk=search_id)
    except SavedSearch.DoesNotExist:
        logging.warn('search_update(%s, using=%r) could not find search',
                     search_id, using)
        return
    search.update(using=using, clear_rejected=True)


@task(ignore_result=True)
@patch_settings
def mark_import_complete(import_app_label, import_model, import_pk,
                         using='default'):
    """
    Checks whether an import is complete, and if it is, gives it an end time.

    """
    import_class = get_model(import_app_label, import_model)
    try:
        source_import = import_class._default_manager.using(using).get(
                                                    pk=import_pk,
                                                    status=import_class.STARTED)
    except import_class.DoesNotExist:
        return

    if (source_import.total_videos is not None and
            (source_import.videos_imported + source_import.videos_skipped
             >= source_import.total_videos)):
        if source_import.auto_approve:
            should_approve = False
            if not SiteLocation.enforce_tiers(using=using):
                should_approve = True
            else:
                remaining_videos = (Tier.get().videos_limit()
                                    - Video.objects.using(using
                                        ).filter(status=Video.ACTIVE).count())
                if remaining_videos > source_import.videos_imported:
                    should_approve = True
            if should_approve:
                source_import.get_videos(using).filter(
                    status=Video.UNAPPROVED).update(
                        status=Video.ACTIVE)
        source_import.status = import_class.COMPLETE
        if import_app_label == 'localtv' and import_model == 'feedimport':
            source_import.source.status = source_import.source.ACTIVE
            source_import.source.save()

    source_import.last_activity = datetime.datetime.now()
    source_import.save()


@task(ignore_result=True)
@patch_settings
def video_from_vidscraper_video(vidscraper_video, site_pk,
                                import_app_label=None, import_model=None,
                                import_pk=None, status=None, author_pks=None,
                                category_pks=None, clear_rejected=False,
                                using='default'):
    if import_app_label is None or import_model is None or import_pk is None:
        source_import = None
    else:
        import_class = get_model(import_app_label, import_model)
        try:
            source_import = import_class.objects.using(using).get(pk=import_pk,
                                                    status=import_class.STARTED)
        except import_class.DoesNotExist:
            logging.debug('Skipping %r: expected import instance missing.',
                          vidscraper_video.url)
            return

    try:
        vidscraper_video.load()
    except Exception, e:
        source_import.handle_error(('Skipped %r: Could not load video data.'
                                     % vidscraper_video.url),
                                   using=using, is_skip=True,
                                   with_exception=True)
        return
        

    if not vidscraper_video.title:
        source_import.handle_error(('Skipped %r: Failed to scrape basic data.'
                                     % vidscraper_video.url),
                                   is_skip=True, using=using)
        return

    if not vidscraper_video.file_url and not vidscraper_video.embed_code:
        source_import.handle_error(('Skipping %r: no file or embed code.'
                                     % vidscraper_video.url),
                                   is_skip=True, using=using)
        return

    site_videos = Video.objects.using(using).filter(site=site_pk)

    if vidscraper_video.guid:
        guid_videos = site_videos.filter(guid=vidscraper_video.guid)
        if clear_rejected:
            guid_videos.rejected().delete()
        if guid_videos.exists():
            source_import.handle_error(('Skipping %r: duplicate guid.'
                                        % vidscraper_video.url),
                                       is_skip=True, using=using)
            return

    if vidscraper_video.link:
        videos_with_link = site_videos.filter(website_url=vidscraper_video.link)
        if clear_rejected:
            videos_with_link.rejected().delete()
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
        
    video = Video.from_vidscraper_video(vidscraper_video, status=status,
                                        using=using, source_import=source_import,
                                        authors=authors, categories=categories,
                                        site_id=site_pk)
    logging.debug('Made video %i: %r', video.pk, video.name)
    if video.thumbnail_url:
        video_save_thumbnail.delay(video.pk, using=using)

@task(ignore_result=True)
@patch_settings
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
        

@task(ignore_result=True)
@patch_settings
def haystack_update_index(app_label, model_name, pk, is_removal,
                          using='default'):
    """
    Updates a haystack index for the given model (specified by ``app_label``
    and ``model_name``). If ``is_removal`` is ``True``, a fake instance is
    constructed with the given ``pk`` and passed to the index's
    :meth:`remove_object` method. Otherwise, the latest version of the instance
    is fetched from the database and passed to the index's
    :meth:`update_object` method.

    """
    model_class = get_model(app_label, model_name)
    search_index = site.get_index(model_class)
    if is_removal:
        instance = model_class(pk=pk)
        search_index.remove_object(instance)
    else:
        try:
            instance = search_index.read_queryset().using(using).get(pk=pk)
        except model_class.DoesNotExist:
            pass
        else:
            search_index.update_object(instance)

@task
@patch_settings
def video_count(using='default'):
    model_class = get_model('localtv', 'Video')
    return settings.ROOT_URLCONF, model_class.objects.db_manager(using).count()
