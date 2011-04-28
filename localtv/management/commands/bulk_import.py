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

import os
import simplejson
import sys

from importlib import import_module

import feedparser

import eventlet
import eventlet.pools

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from vidscraper.bulk_import import bulk_import_url_list, bulk_import

from localtv import models
import localtv.util
import localtv.tasks

DEFAULT_HTTPLIB_CACHE_PATH='/tmp/.cache-for-uid-%d' % os.getuid()

class Command(BaseCommand):

    args = '[feed primary key]'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('bulk_import takes one argument: '
                               '%i argument(s) given' % len(args))
        try:
            feed = models.Feed.objects.get(pk=args[0])
        except models.Feed.DoesNotExist:
            raise CommandError('Feed with pk %s does not exist' % args[0])

        try:
            self.verbose = (int(options['verbosity']) > 1)
        except (KeyError, ValueError):
            self.verbose = False

        httplib2 = eventlet.import_patched('httplib2')

        # Use httplib2 to GET the feed.
        # This permits us to download it only once, passing a parsed_feed through
        # to the vidscraper functions.
        h = httplib2.Http(DEFAULT_HTTPLIB_CACHE_PATH)

        response, content = h.request(feed.feed_url, 'GET')
        parsed_feed = feedparser.parse(content)

        # Try to work asynchronously, calling feedparser ourselves. We can do that
        # if the importer supports bulk_import_url_list.
        feed_urls = bulk_import_url_list(parsed_feed=parsed_feed)
        if type(feed_urls) != list: # hack.
            return self.use_old_bulk_import(parsed_feed, feed)
        else:
            self.celery_tasks = {}
            video_ids = self.bulk_import_asynchronously(parsed_feed, h, feed_urls, feed)
            self.enqueue_celery_tasks_for_thumbnail_fetches(video_ids)


    @transaction.commit_manually
    def bulk_import_asynchronously(self, original_parsed_feed, h, feed_urls, feed):
        # This asynchronous bulk_import is a parallelism monster.

        # We do as much network I/O as we can using eventlet,
        # rather than threads or subprocesses.
        httplib2 = eventlet.import_patched('httplib2')

        httppool = eventlet.pools.Pool(max_size=200)
        httppool.create = lambda: httplib2.Http(DEFAULT_HTTPLIB_CACHE_PATH)

        pool = eventlet.GreenPool(100)

        def get_url(url):
            with httppool.item() as http:
                if self.verbose:
                    print 'getting', url
                resp, content = http.request(url, 'GET')
                return (resp, content)

        def cache_thumbnail_url(url):
            with httppool.item() as http:
                if self.verbose:
                    print 'getting thumb', url
                localtv.util.cache_downloaded_file(url, http)

        stats = {
            'total': 0,
            'imported': 0,
            'skipped': 0
            }

        def handle_one_sub_feed(feed_contents):
            parsed_feed = feedparser.parse(feed_contents)
            # For each feed entry in this small sub-feed, handle the item.
            for index, entry in enumerate(parsed_feed['entries'][::-1]):
                yield handle_one_item(index, parsed_feed, entry)

        def handle_one_item(index, parsed_feed, entry):
            i = feed._handle_one_bulk_import_feed_entry(index, parsed_feed, entry, verbose=self.verbose, clear_rejected=False,
                                                        actually_save_thumbnails=False)
            # Enqueue the work to download the thumbnail
            if i['video']:
                v = i['video']
                thumbnail_url = v.thumbnail_url
                if thumbnail_url:
                    cache_thumbnail_url(thumbnail_url)

            stats['total'] += 1
            if i['video'] is not None:
                stats['imported'] += 1
            else:
                stats['skipped'] += 1

            return i

        results = []
        for (response, content) in pool.imap(get_url, feed_urls):
            try:
                # We make it a list so that we can iterate across
                # it more than once.
                result = list(handle_one_sub_feed(content))
            except:
                transaction.rollback()
                raise
            else:
                transaction.commit()

            try:
                results.extend(result)
                # Now that handle_one_sub_feed has finished, it is
                # safe to spawn celery tasks to do thumbnail fetching.
                for video in [i['video'] for i in result]:
                    if video:
                        self._enqueue_one_celery_task_for_thumbnail_fetch(video.id)
            except:
                transaction.rollback()
                raise
            else:
                transaction.commit()

        # Get all the thumbnail URLs, and once you have them
        pool.waitall() # wait for the thumbnails

        try:
            # Finish marking the Feed as imported.
            feed._mark_bulk_import_as_done(original_parsed_feed)

            feed.status = models.FEED_STATUS_ACTIVE
            feed.save()
            return_me = [i['video'].id for i in results if i['video']]
        except:
            transaction.rollback()
            raise
        else:
            transaction.commit()

        print simplejson.dumps(stats),
        return return_me

    def _enqueue_one_celery_task_for_thumbnail_fetch(self, video_id):
        if self.verbose:
            print 'Starting thumbnail fetches for', video_id

        mod = import_module(settings.SETTINGS_MODULE)
        manage_py = os.path.abspath(os.path.join(
                os.path.dirname(mod.__file__),
                'manage.py'))

        task = localtv.tasks.check_call.delay((
                getattr(settings, 'PYTHON_EXECUTABLE', sys.executable),
                manage_py,
                'update_one_thumbnail',
                video_id))
        self.celery_tasks[video_id] = task

    def enqueue_celery_tasks_for_thumbnail_fetches(self, video_ids):
        for video_id in video_ids:
            if video_id in self.celery_tasks:
                continue
            self._enqueue_one_celery_task_for_thumbnail_fetch(video_id)

        if self.verbose:
            print 'Enqueued all thumbnail fetches.'

        # Finally, wait for them all to finish
        for video_id in self.celery_tasks:
            task = self.celery_tasks[video_id]
            task.get()

        if self.verbose:
            print 'Finished thumbnail fetches.'

    def use_old_bulk_import(self, parsed_feed, feed):
        bulk_feed = bulk_import(feed_url=None, parsed_feed=parsed_feed)

        stats = {
            'total': 0,
            'imported': 0,
            'skipped': 0
            }
        try:
            for i in feed._update_items_generator(verbose=self.verbose,
                                                  parsed_feed=bulk_feed,
                                                  clear_rejected=True,
                                                  actually_save_thumbnails=True):
                if not models.Feed.objects.filter(pk=feed.pk).count():
                    # someone deleted the feed, quit
                    break
                stats['total'] += 1
                if i['video'] is not None:
                    stats['imported'] += 1
                else:
                    stats['skipped'] += 1
        finally:
            feed.status = models.FEED_STATUS_ACTIVE
            feed.save()
        print simplejson.dumps(stats),
