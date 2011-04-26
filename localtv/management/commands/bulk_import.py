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

import feedparser

import eventlet
import eventlet.pools

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from vidscraper.bulk_import import bulk_import_url_list, bulk_import

from localtv import models

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
            verbose = (int(options['verbosity']) > 1)
        except (KeyError, ValueError):
            verbose = False

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
            return self.use_old_bulk_import(parsed_feed, feed, verbose)
        else:
            return self.bulk_import_asynchronously(parsed_feed, h, feed_urls, feed, verbose)


    @transaction.commit_on_success
    def bulk_import_asynchronously(self, original_parsed_feed, h, feed_urls, feed, verbose):
        httplib2 = eventlet.import_patched('httplib2')

        httppool = eventlet.pools.Pool(max_size=10)
        httppool.create = lambda: httplib2.Http(DEFAULT_HTTPLIB_CACHE_PATH)

        def get_url(url):
            with httppool.item() as http:
                resp, content = http.request(url, 'GET')
                return (resp, content)

        stats = {
            'total': 0,
            'imported': 0,
            'skipped': 0
            }

        def handle_one_sub_feed(feed_contents):
            print 'ho'
            parsed_feed = feedparser.parse(feed_contents)
            # For each feed entry in this small sub-feed, handle the item.
            for index, entry in enumerate(parsed_feed['entries'][::-1]):
                handle_one_item(index, parsed_feed, entry)

        def handle_one_item(index, parsed_feed, entry):
            print 'hee'
            i = feed._handle_one_bulk_import_feed_entry(index, parsed_feed, entry, verbose=verbose, clear_rejected=False,
                                                        actually_save_thumbnails=False)
            stats['total'] += 1
            if i['video'] is not None:
                stats['imported'] += 1
            else:
                stats['skipped'] += 1

        pool = eventlet.GreenPool(100)
        for (response, content) in pool.imap(get_url, feed_urls):
            handle_one_sub_feed(content)

        # Finish marking the Feed as imported.
        feed._mark_bulk_import_as_done(original_parsed_feed)

    def use_old_bulk_import(self, parsed_feed, feed, verbose):
        bulk_feed = bulk_import(feed_url=None, parsed_feed=parsed_feed)

        stats = {
            'total': 0,
            'imported': 0,
            'skipped': 0
            }
        try:
            for i in feed._update_items_generator(verbose=verbose,
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
