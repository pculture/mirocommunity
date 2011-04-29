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
import multiprocessing

import feedparser

import eventlet
import eventlet.pools

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from vidscraper.bulk_import import bulk_import_url_list, bulk_import

from localtv import models
import localtv.util
import localtv.tasks

DEFAULT_HTTPLIB_CACHE_PATH='/tmp/.cache-for-uid-%d' % os.getuid()

def function_for_fork_worker(data_tuple):
    video_id, future_status = data_tuple
    import logging
    import localtv.management.commands.update_one_thumbnail
    cmd = localtv.management.commands.update_one_thumbnail.Command()
    try:
        cmd.handle(video_id, future_status)
    except models.Video.DoesNotExist:
        logging.warn("For some reason, we failed to find the model with ID %d" % (
                video_id, ))
        return False # Aww, shucks. Maybe after a retry this will work.
    except Exception, e:
        logging.warn("uh, bizarre -- the task fell over. Maybe it will work on a retry.")
        logging.exception(e)
        return False
    return True

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
        try:
            feed_urls = bulk_import_url_list(parsed_feed=parsed_feed)
        except ValueError:
            return self.use_old_bulk_import(parsed_feed, feed)
        # Okay, good, we either got the feed_url list, or we passed the work
        # off the old-style function. Proceed.
        self.forked_tasks = {}
        self.forked_task_worker_pool =  multiprocessing.Pool(processes=8)
        # start 8 worker processes. That should be fine, right?
        self.bulk_import_asynchronously(parsed_feed, h, feed_urls, feed)
        self.enqueue_forked_tasks_for_thumbnail_fetches(feed)

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

                # The _handle_one_bulk_import_feed_entry() method gave the
                # video a status, but we have to take that back for now.
                #
                # We set the status to VIDEO_STATUS_PENDING_THUMBNAIL so that
                # no one can see the video until the thumbnailing process is
                # complete.
                #
                # We pass the thumbnailer the status that the video should get
                # so that it can set that once it is ready.
                i['future_status'] = v.status
                v.status = models.VIDEO_STATUS_PENDING_THUMBNAIL
                v.save()

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
                # safe to spawn forked tasks to do thumbnail fetching.
                for i in result:
                    video = i['video']
                    if video:
                        future_status = i['future_status']
                        self._enqueue_one_forked_task_for_thumbnail_fetch(
                            video.id, future_status)
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

    def _enqueue_one_forked_task_for_thumbnail_fetch(self, video_id, future_status):
        if self.verbose:
            print 'Starting thumbnail fetches for', video_id

        task = self.forked_task_worker_pool.apply_async(
            function_for_fork_worker, [(video_id, future_status)])
        self.forked_tasks[video_id] = task

    def enqueue_forked_tasks_for_thumbnail_fetches(self, feed):
        # Make sure that any videos from the feed with
        # status=models.VIDEO_STATUS_PENDING_THUMBNAIL have tasks.
        all_feed_items_pending_thumbnail = feed.video_set.filter(
            status=models.VIDEO_STATUS_PENDING_THUMBNAIL)

        for video in all_feed_items_pending_thumbnail:
            if video.id in self.forked_tasks:
                continue
            # Eek. It seems we have to grab a thumbnail for a video
            # where we misplaced the forked task. In that case, we
            # have to look at the feed to see what status videos
            # should get.
            self._enqueue_one_forked_task_for_thumbnail_fetch(
                video.id, feed.default_video_status())

        if self.verbose:
            print 'Enqueued all thumbnail fetches.'

        # Finally, wait for them all to finish
        for video_id in self.forked_tasks:
            task = self.forked_tasks[video_id]
            success = task.get()
            if not success:
                # Re-enqueue it. :-(
                self._enqueue_one_forked_task_for_thumbnail_fetch(
                    video_id, feed.default_video_status())

        for video_id in self.forked_tasks:
            task = self.forked_tasks[video_id]
            success = task.get()

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
