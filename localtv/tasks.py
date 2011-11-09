g# This file is part of Miro Community.
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

import os

import logging
import subprocess

import vidscraper

from celery.task import task
from django.conf import settings
from django.db.models.loading import get_model
from django.contrib.auth.models import User
from haystack import site

from localtv import utils
from localtv.models import Video, Feed, SiteLocation, CannotOpenImageUrl

#import eventlet.debug
#eventlet.debug.hub_blocking_detection(True)

if hasattr(settings.DATABASES, 'module'):
    def patch_settings(func):
        def wrapper(*args, **kwargs):
            using = kwargs.get('using', None)
            if using in (None, 'default',
                         settings.SETTINGS_MODULE.split('.')[0]):
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
            

@task
def check_call(args, env={}):
    args = [str(arg) for arg in args]
    environ = os.environ.copy()
    environ.update(env)
    process = subprocess.Popen(
        args,
        executable=args[0],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environ)

    stderr = []
    while process.poll() is None:
        # #17982: the stderr buffer can fill, so make sure to pull the data
        # out of the buffer
        err = process.stderr.read()
        if err:
            stderr.append(err)

    return_code = process.wait()
    if return_code: # some problem with the code
        while stderr[-1] != '':
            stderr.append(process.stderr.read())

        raise RuntimeError('Error during: %s\n\nTraceback:\n%s' % (
                ' '.join(args), ''.join(stderr)))
    else: # imported the feed correctly
        stdout = [process.stdout.read()]
        while stdout[-1] != '':
            stdout.append(process.stdout.read())
        return ''.join(stdout)

@task(ignore_result=True)
@patch_settings
def bulk_import(feed_id, crawl=False, using='default'):
    try:
        feed = Feed.objects.using(using).get(pk=feed_id)
    except Feed.DoesNotExist:
        logging.warn('bulk_import(%s, using=%r) could not find feed',
                     feed_id, using)
    sl = SiteLocation.objects.db_manager(using).get_current()
    if not sl.enforce_tiers(using=using):
        max_results = 1000 # None
    else:
        max_results = sl.get_tier().remaining_videos()

    video_iter = vidscraper.auto_feed(
        feed.feed_url, crawl=crawl, max_results=max_results)
    video_iter.load()
    logging.debug('loaded object: %r', video_iter)
    logging.debug('loaded feed: %r', video_iter.title)
    logging.debug('entry count: %s', video_iter.entry_count)
    try:
        feed.update_items(
            clear_rejected=True,
            video_iter=video_iter)
    finally:
        feed.status = Feed.ACTIVE
        feed.save()

@task(ignore_result=True)
@patch_settings
def video_from_vidscraper_video(vidscraper_video, source,
                                clear_rejected=False, using='default',
                                **kwargs):
    try:
        vidscraper_video.load()
    except Exception:
        logging.debug('exception loading video from %r', vidscraper_video.url,
                      with_exception=True)

    if not vidscraper_video.file_url and not vidscraper_video.embed_code:
        logging.debug('skipping %r: no file_url or embed code',
                      vidscraper_video.url)
        return
    if vidscraper_video.guid:
        guids = source.video_set.filter(guid=vidscraper_video.guid)
        if guids.exists():
            logging.debug('skipping %r: duplicate guid',
                          vidscraper_video.url)
            return
    elif vidscraper_video.link:
        videos_with_link = Video.objects.filter(
            website_url=vidscraper_video.link)
        if clear_rejected:
            videos_with_link.rejected().delete()
        if videos_with_link.exists():
            logging.debug('skipping %r: duplicate link',
                          vidscraper_video.url)
    if 'authors' not in kwargs and vidscraper_video.user:
        name = vidscraper_video.user
        if ' ' in name:
            first, last = name.split(' ', 1)
        else:
            first, last = name, ''
        author, created = User.objects.get_or_create(
            username=name[:30],
            defaults={'first_name': first[:30],
                      'last_name': last[:30]})
        if created:
            author.set_unusable_password()
            author.save()
        utils.get_profile_model().objects.create(
            user=author,
            website=vidscraper_video.user_url or '')
        kwargs['authors'] = [author]
        
    video = Video.from_vidscraper_video(vidscraper_video,
                                        using=using,
                                        **kwargs)
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
            'video_save_thumbnails(%s, using=%r) could not find video',
            video_pk, using)
    try:
        v.save_thumbnail()
    except CannotOpenImageUrl:
        return video_save_thumbnail.retry((video_pk,), {'using': using})
        

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
    print 'VIDEO COUNT USING', using
    model_class = get_model('localtv', 'Video')
    return settings.ROOT_URLCONF, model_class.objects.db_manager(using).count()
