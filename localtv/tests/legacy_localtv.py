# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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

import json
import datetime
import logging
import os.path
import shutil
import tempfile
from urllib import quote_plus, urlencode

import mock

import feedparser
import vidscraper

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.comments import get_model, get_form, get_form_target
Comment = get_model()
CommentForm = get_form()

from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sites.models import Site
from django.core.files.base import File
from django.core.files import storage
from django.core import mail
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpRequest
from django.test import TestCase
from django.test.client import Client, RequestFactory

from haystack import connections
from haystack.query import SearchQuerySet

import localtv.settings
import localtv.templatetags.filters
from localtv.middleware import UserIsAdminMiddleware
from localtv import models
from localtv.models import (Watch, Category, SiteSettings, Video, TierInfo,
                            Feed, OriginalVideo, SavedSearch, FeedImport,
                            Source)
from localtv import utils
import localtv.feeds.views

from notification import models as notification
from tagging.models import Tag


Profile = utils.get_profile_model()
NAME_TO_COST = localtv.tiers.Tier.NAME_TO_COST()
PLUS_COST = NAME_TO_COST['plus']
PREMIUM_COST = NAME_TO_COST['premium']
MAX_COST = NAME_TO_COST['max']


class FakeRequestFactory(RequestFactory):
    """Constructs requests with any necessary attributes set."""
    def request(self, **request):
        request = super(FakeRequestFactory, self).request(**request)
        request.user = AnonymousUser()
        UserIsAdminMiddleware().process_request(request)
        SessionMiddleware().process_request(request)
        return request


class BaseTestCase(TestCase):
    fixtures = ['site', 'users']
    target_tier_name = 'max'

    def run(self, *args, **kwargs):
        # hack to prevent the test runner from treating abstract classes as
        # something with tests to run
        if self.__class__.__dict__.get('abstract'):
            return
        else:
            return TestCase.run(self, *args, **kwargs)

    def setUp(self):
        TestCase.setUp(self)
        self.old_site_id = settings.SITE_ID
        settings.SITE_ID = 1
        self.old_DISABLE = localtv.settings.DISABLE_TIERS_ENFORCEMENT
        localtv.settings.DISABLE_TIERS_ENFORCEMENT = False
        SiteSettings.objects.clear_cache()
        self.site_settings = SiteSettings.objects.get_current()
        self.tier_info = TierInfo.objects.get_current()

        self._switch_into_tier()
        self._rebuild_index()

        self.old_MEDIA_ROOT = settings.MEDIA_ROOT
        self.tmpdir = tempfile.mkdtemp()
        settings.MEDIA_ROOT = self.tmpdir
        Profile.__dict__['logo'].field.storage = \
            storage.FileSystemStorage(self.tmpdir)
        self.old_CACHES = settings.CACHES
        settings.CACHES = {
            'default':
                {'BACKEND':
                     'django.core.cache.backends.dummy.DummyCache'}}
        mail.outbox = [] # reset any email at the start of the suite
        self.factory = FakeRequestFactory()

    def _switch_into_tier(self):
        # By default, tests run on an 'max' account.
        if self.site_settings.tier_name != self.target_tier_name:
            self.site_settings.tier_name = self.target_tier_name
            self.site_settings.save()

    def tearDown(self):
        TestCase.tearDown(self)
        settings.SITE_ID = self.old_site_id
        settings.MEDIA_ROOT = self.old_MEDIA_ROOT
        localtv.settings.DISABLE_TIERS_ENFORCEMENT = self.old_DISABLE
        settings.CACHES = self.old_CACHES
        Profile.__dict__['logo'].field.storage = \
            storage.default_storage
        shutil.rmtree(self.tmpdir)

    def _data_file(self, filename):
        """
        Returns the absolute path to a file in our testdata directory.
        """
        return os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                'testdata',
                filename))

    def assertStatusCodeEquals(self, response, status_code):
        """
        Assert that the response has the given status code.  If not, give a
        useful error mesage.
        """
        self.assertEqual(response.status_code, status_code,
                          'Status Code: %i != %i\nData: %s' % (
                response.status_code, status_code,
                response.content or response.get('Location', '')))

    def assertRequiresAuthentication(self, url, *args,
                                     **kwargs):
        """
        Assert that the given URL requires the user to be authenticated.

        If additional arguments are passed, they are passed to the Client.get
        method

        If keyword arguments are present, they're passed to Client.login before
        the URL is accessed.

        @param url_or_reverse: the URL to access
        """
        c = Client()

        if kwargs:
            c.login(**kwargs)

        response = c.get(url, *args)
        if args and args[0]:
            url = '%s?%s' % (url, urlencode(args[0]))
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s?next=%s' %
                          ('testserver',
                           settings.LOGIN_URL,
                           quote_plus(url, safe='/')))
    def _clear_index(self):
        """Clears the search index."""
        backend = connections['default'].get_backend()
        backend.clear()

    def _update_index(self):
        """Updates the search index."""
        backend = connections['default'].get_backend()
        index = connections['default'].get_unified_index().get_index(Video)
        backend.update(index, index.index_queryset())
        
    def _rebuild_index(self):
        """Clears and then updates the search index."""
        self._clear_index()
        self._update_index()


# -----------------------------------------------------------------------------
# Feed tests
# -----------------------------------------------------------------------------

class FeedImportTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['feeds']

    def setUp(self):
        BaseTestCase.setUp(self)
        self._parsed_feed = list(self._parse_feed('feed.rss'))

    def _parse_feed(self, filename, force_url=False):
        """
        Returns a :class:`vidscraper.suites.base.Feed` for the feed stored as
        <filename> in our testdata.  If `force_url` is True, we'll load the URL
        from the feed and use that to get a suite.
        """
        path = self._data_file(filename)
        if force_url:
            fp = feedparser.parse(path)
            vidscraper_feed = vidscraper.auto_feed(fp.feed.link)
            vidscraper_feed.get_first_url = lambda: path
        else:
            vidscraper_feed = vidscraper.auto_feed(path)
        return vidscraper_feed

    def _update_with_video_iter(self, video_iter, feed):
        feed_import = FeedImport.objects.create(source=feed,
                                                auto_approve=feed.auto_approve)
        Source.update(feed, video_iter, feed_import)


    def test_update_approved_feed(self):
        feed = Feed.objects.get(pk=1)
        feed.status = Feed.INACTIVE
        feed.save()
        self._update_with_video_iter(self._parsed_feed, feed)
        feed = Feed.objects.get(pk=1)
        self.assertEqual(feed.status, Feed.ACTIVE)

    def test_auto_approve_True(self):
        """
        If Feed.auto_approve is True, the imported videos should be marked as
        active.
        """
        feed = Feed.objects.get(pk=1)
        feed.auto_approve = True
        self._update_with_video_iter(self._parsed_feed, feed)
        self.assertEqual(Video.objects.count(), 5)
        self.assertEqual(Video.objects.filter(
                status=Video.ACTIVE).count(), 5)

    @mock.patch('localtv.tiers.Tier.videos_limit', lambda *args: 4)
    def test_auto_approve_True_when_user_past_video_limit(self):
        """
        If FeedImport.auto_approve is True, but approving the videos in the feed
        would put the site past the video limit, the imported videos should be
        marked as unapproved.

        """
        feed = Feed.objects.get(pk=1)
        feed.auto_approve = True
        self._update_with_video_iter(self._parsed_feed, feed)
        self.assertEqual(Video.objects.count(), 5)
        self.assertEqual(Video.objects.filter(
                status=Video.ACTIVE).count(), 4)
        self.assertEqual(Video.objects.filter(
                status=Video.UNAPPROVED).count(), 1)

    def test_auto_approve_False(self):
        """
        If Feed.auto_approve is False, the imported videos should be marked as
        unapproved.
        """
        feed = Feed.objects.get(pk=1)
        feed.auto_approve = False
        self._update_with_video_iter(self._parsed_feed, feed)
        self.assertEqual(Video.objects.count(), 5)
        self.assertEqual(Video.objects.filter(
                status=Video.UNAPPROVED).count(), 5)

    def test_entries_inserted_in_feed_order(self):
        """
        When adding entries from a feed, they should be sortable so that the
        first item in the feed is the first item returned.
        """
        feed = Feed.objects.get(pk=1)
        self._update_with_video_iter(self._parsed_feed, feed)
        parsed_guids = [entry.guid for entry in self._parsed_feed]
        db_guids = Video.objects.in_feed_order().values_list('guid',
                                                             flat=True)
        self.assertEqual(list(parsed_guids), list(db_guids))

    def test_ignore_duplicate_guid(self):
        """
        If an item with a certain GUID is in a feed twice, but not in the
        database at all, it should only be imported once.
        """
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed_with_duplicate_guid.rss')
        self._update_with_video_iter(video_iter, feed)
        feed_import = FeedImport.objects.filter(source=feed).latest()
        self.assertEqual(feed_import.videos_skipped, 1)
        self.assertEqual(feed_import.videos_imported, 1)
        self.assertEqual(Video.objects.count(), 1)

    def test_ignore_duplicate_link(self):
        """
        If an item with a certain link is in a feed twice, but not in the
        database at all, it should only be imported once.
        """
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed_with_duplicate_link.rss')
        self._update_with_video_iter(video_iter, feed)
        feed_import = FeedImport.objects.filter(source=feed).latest()
        self.assertEqual(feed_import.videos_skipped, 1)
        self.assertEqual(feed_import.videos_imported, 1)
        self.assertEqual(Video.objects.count(), 1)

    def test_entries_include_feed_data(self):
        """
        Videos imported from feeds should pull the following from the RSS feed:
        * GUID
        * name
        * description (sanitized)
        * website URL
        * publish date
        * file URL
        * file length
        * file MIME type
        * thumbnail
        * tags
        """
        feed = Feed.objects.get(pk=1)
        self._update_with_video_iter(self._parsed_feed, feed)
        video = Video.objects.in_feed_order().reverse()[0]
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.guid, u'23C59362-FC55-11DC-AF3F-9C4011C4A055')
        self.assertEqual(video.name, u'Dave Glassco Supports Miro')
        self.assertEqual(video.description,
                          '>\n\n<br />\n\nDave is a great advocate and '
                          'supporter of Miro.')
        self.assertEqual(video.website_url, 'http://blip.tv/file/779122')
        self.assertEqual(video.file_url,
                          'http://blip.tv/file/get/'
                          'Miropcf-DaveGlasscoSupportsMiro942.mp4')
        self.assertEqual(video.file_url_length, 16018279)
        self.assertEqual(video.file_url_mimetype, 'video/mp4')
        self.assertTrue(video.has_thumbnail)
        self.assertEqual(video.thumbnail_url,
                          'http://a.images.blip.tv/'
                          'Miropcf-DaveGlasscoSupportsMiro959.jpg')
        self.assertEqual(video.when_published,
                          datetime.datetime(2008, 3, 27, 23, 25, 51))
        self.assertEqual(video.video_service(), 'blip.tv')
        category = ['Default Category']
        if getattr(settings, 'FORCE_LOWERCASE_TAGS', False):
            category = [category[0].lower()]
        self.assertEqual([tag.name for tag in video.tags.all()],
                          category)

    def test_entries_link_optional(self):
        """
        A link in the feed to the original source should be optional.
        """
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed_without_link.rss')
        self._update_with_video_iter(video_iter, feed)
        video = Video.objects.in_feed_order().reverse()[0]
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.guid, u'D9E50330-F6E1-11DD-A117-BB8AB007511B')

    def test_entries_enclosure_type_optional(self):
        """
        An enclosure without a MIME type, but with a file URL extension we
        think is media, should be imported.
        """
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed_without_mime_type.rss')
        self._update_with_video_iter(video_iter, feed)
        video = Video.objects.in_feed_order().reverse()[0]
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.guid, u'D9E50330-F6E1-11DD-A117-BB8AB007511B')

    def test_entries_vimeo(self):
        """
        Vimeo RSS feeds should include the correct data.
        """
        feed = Feed.objects.get(pk=1)
        feed.auto_authors = []
        video_iter = vidscraper.auto_feed('http://vimeo.com/user1751935/videos/')
        video_iter.get_url_response = lambda u: json.load(file(
                self._data_file('vimeo.json')))
        self._update_with_video_iter(video_iter, feed)
        video = Video.objects.in_feed_order().reverse()[0]
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.guid, u'tag:vimeo,2009-12-04:clip7981161')
        self.assertEqual(video.name, u'Tishana - Pro-Choicers on Stupak')
        self.assertEqual(video.description, '\
Tishana from SPARK Reproductive Justice talking about the right to choose \
after the National Day of Action Rally to Stop Stupak-Pitts, 12.2.2009')
        self.assertEqual(video.website_url, 'http://vimeo.com/7981161')
        self.assertTrue('vimeo.com' in video.embed_code)
        self.assertTrue('<iframe ' in video.embed_code or
                        '<object ' in video.embed_code)
        self.assertEqual(video.file_url, '')
        self.assertTrue(video.has_thumbnail)
        self.assertTrue(video.thumbnail_url.endswith('.jpg'),
                        video.thumbnail_url)
        self.assertEqual(video.when_published,
                          datetime.datetime(2009, 12, 4, 8, 23, 47))
        self.assertEqual(video.video_service(), 'Vimeo')
        category = ['Pro-Choice', 'Stupak-Pitts']
        if getattr(settings, 'FORCE_LOWERCASE_TAGS', False):
            category = [cat.lower() for cat in category]
        self.assertEqual([tag.name for tag in video.tags.all()],
                          category)

        # no automatic author, so it should be the user from the site
        self.assertEqual(list(video.authors.values_list('username')),
                          [('Latoya Peterson',)])
        self.assertEqual(video.authors.get().get_profile().website,
                          'http://vimeo.com/user1751935')

    def test_entries_youtube(self):
        """
        Youtube RSS feeds should include the correct data.
        """
        feed = Feed.objects.get(pk=1)
        user = User.objects.get(pk=1)
        feed.auto_authors = [user]
        feed.save()
        video_iter = self._parse_feed('youtube.rss', force_url=True)
        self._update_with_video_iter(video_iter, feed)
        video = Video.objects.in_feed_order().reverse()[0]
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.guid,
                          u'http://gdata.youtube.com/feeds/api/videos/BBwtzeZdoHQ')
        self.assertEqual(video.name,
                          'Dr. Janice Key Answers Questions about Preventing '
                          'Teen Pregnancy')
        self.assertEqual(video.description, "\
Dr. Janice Key, Professor of Adolescent Medicine at the Medical \
University South Carolina, answers questions about teen pregnancy prevention.")
        self.assertEqual(video.website_url,
                          'http://www.youtube.com/watch?v=BBwtzeZdoHQ')
        self.assertTrue('/BBwtzeZdoHQ' in video.embed_code)
        self.assertEqual(video.file_url, '')
        self.assertTrue(video.has_thumbnail)
        self.assertTrue('BBwtzeZdoHQ' in video.thumbnail_url)
        self.assertEqual(video.when_published,
                          datetime.datetime(2010, 1, 18, 19, 41, 21))
        self.assertEqual(video.video_service(), 'YouTube')
        category = ['Nonprofit']
        if getattr(settings, 'FORCE_LOWERCASE_TAGS', False):
            category = [cat.lower() for cat in category]
        self.assertEqual([tag.name for tag in video.tags.all()],
                          category)

        # auto author should be assigned
        self.assertEqual(list(video.authors.all()),
                          [user])

    def test_entries_atom(self):
        """
        Atom feeds should be handled correctly,
        """
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed.atom')
        self._update_with_video_iter(video_iter, feed)
        video = Video.objects.order_by('id')[0]
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.guid, u'http://www.example.org/entries/1')
        self.assertEqual(video.name, u'Atom 1.0')
        self.assertEqual(video.when_published, datetime.datetime(2005, 7, 15,
                                                                  12, 0, 0))
        self.assertEqual(video.file_url,
                          u'http://www.example.org/myvideo.ogg')
        self.assertEqual(video.file_url_length, 1234)
        self.assertEqual(video.file_url_mimetype, u'application/ogg')
        self.assertEqual(video.website_url,
                          u'http://www.example.org/entries/1')
        self.assertEqual(video.description, u"""<h1>Show Notes</h1>
<ul>
<li>00:01:00 -- Introduction</li>
<li>00:15:00 -- Talking about Atom 1.0</li>
<li>00:30:00 -- Wrapping up</li>
</ul>""")

    def test_entries_atom_from_mc(self):
        """
        Atom feeds generated by Miro Community should be handled as if the item
        was imported from the original feed.
        """
        self.maxDiff = None
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed_from_mc.atom')
        self._update_with_video_iter(video_iter, feed)
        video = Video.objects.order_by('id')[0]
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.guid,
                          u'http://www.onnetworks.com/5843 at '
                          'http://www.onnetworks.com')
        self.assertEqual(video.name, u'"The Dancer & Kenaudra"')
        self.assertEqual(video.when_published,
                          datetime.datetime(2009, 1, 13, 6, 0))
        self.assertEqual(video.file_url,
                          u'http://podcast.onnetworks.com/videos/'
                          'sgatp_0108_kenaudra_480x270.mp4?feed=video'
                          '&key=6100&target=itunes')
        self.assertEqual(video.file_url_length, 1)
        self.assertEqual(video.file_url_mimetype, u'video/mp4')
        self.assertEqual(video.website_url,
                          u'http://www.onnetworks.com/videos/'
                          'smart-girls-at-the-party/the-dancer-kenaudra')
        self.assertEqual(video.description,
                          u'Kenaudra displays her many talents including a '
                          'new dance called Praise Dancing.<br />'
                          '<a href="http://www.onnetworks.com/videos/'
                          'smart-girls-at-the-party/the-dancer-kenaudra"></a>')
        self.assertEqual(video.embed_code,
                          u'<object width="425" height="271">'
                          '<embed id="ONPlayerEmbed" width="425" height="271" '
                          'allowfullscreen="true" flashvars="configFileName='
                          'http://www.onnetworks.com/embed_player/videos/'
                          'smart-girls-at-the-party/the-dancer-kenaudra?'
                          'target=site" scale="aspect" '
                          'allowscriptaccess="always" allownetworking="all" '
                          'quality="high" bgcolor="#ffffff" name="ONPlayer" '
                          'style="" src="http://www.onnetworks.com/swfs/'
                          'ONPlayerEmbed.swf/product_id=sgatp_0108_kenaudra/'
                          'cspid=4b2678259ccf1f2b" '
                          'type="application/x-shockwave-flash"></embed>'
                          '</object>')

    def test_entries_atom_with_link_via(self):
        """
        Atom feeds with <link rel="via"> should use the via URL as the website
        URL.
        """
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed_with_link_via.atom')
        self._update_with_video_iter(video_iter, feed)
        video = Video.objects.in_feed_order().reverse()[0]
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.website_url,
                          u'http://www.example.org/entries/1')

    def test_entries_atom_with_media(self):
        """
        Atom feeds that use Yahoo!'s Media RSS specification should also have
        their content imported,
        """
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed_with_media.atom')
        self._update_with_video_iter(video_iter, feed)
        video = Video.objects.in_feed_order().reverse()[0]
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.file_url,
                          u'http://www.example.org/myvideo.ogg')
        self.assertEqual(video.file_url_mimetype, u'application/ogg')
        self.assertEqual(video.thumbnail_url,
                          'http://www.example.org/myvideo.jpg')

    def test_entries_atom_with_media_player(self):
        """
        Atom feeds that use Yahoo!'s Media RSS specification to include an
        embeddable player (with <media:player> should have that code included,
        """
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed_with_media_player.atom')
        self._update_with_video_iter(video_iter, feed)
        video = Video.objects.in_feed_order().reverse()[0]
        self.assertEqual(video.feed, feed)
        self.assertEqual(video.embed_code,
                          '<embed src="http://www.example.org/?a=b&c=d">')

    def test_entries_atom_with_invalid_media(self):
        """
        Atom feeds that incorrectly use Yahoo!'s Media RSS specification (and
        don't specify a video another way) should be ignored.
        """
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed_with_invalid_media.atom')
        self._update_with_video_iter(video_iter, feed)
        self.assertEqual(feed.video_set.count(), 0)

    def test_entries_atom_with_long_item(self):
        """
        Feeds with long file URLs (>200 characters) should have them shortened
        so they fit in the database.
        """
        if not getattr(settings, 'BITLY_LOGIN', None):
            logging.warn(
                'skipping FeedImportTestCase.test_entries_atom_with_long_item:'
                ' cannot shorten URLs without BITLY_LOGIN')
            return
        feed = Feed.objects.get(pk=1)
        video_iter = self._parse_feed('feed_with_long_item.atom')
        self._update_with_video_iter(video_iter, feed)
        self.assertEqual(feed.video_set.count(), 1)


    def test_entries_multiple_imports(self):
        """
        Importing a feed multiple times shouldn't overwrite the existing
        videos.
        """
        feed = Feed.objects.get(pk=1)
        video_iter = list(self._parse_feed('feed_with_media_player.atom'))
        self._update_with_video_iter(video_iter, feed)
        self.assertEqual(feed.video_set.count(), 1)
        self.assertEqual(feed.imports.latest().videos_imported, 1)
        v = feed.video_set.get()
        # didn't get any updates
        self._update_with_video_iter(video_iter, feed)
        self.assertEqual(feed.video_set.count(), 1)
        self.assertEqual(feed.imports.latest().videos_imported, 0)
        v2 = feed.video_set.get()
        self.assertEqual(v.pk, v2.pk)

    def test_video_service(self):
        """
        Feed.video_service() should return the name of the video service that
        the feed comes from.  If it doesn't come from a known service, it
        should return None.
        """
        services = (
            ('YouTube',
             'http://gdata.youtube.com/feeds/base/standardfeeds/top_rated'),
            ('YouTube',
             'http://www.youtube.com/rss/user/test/video.rss'),
            ('blip.tv', 'http://miropcf.blip.tv/rss'),
            ('Vimeo', 'http://vimeo.com/tag:miro/rss'))

        feed = Feed.objects.get(pk=1)
        for service, url in services:
            feed.feed_url = url
            self.assertEqual(feed.video_service(), service,
                              '%s was incorrectly described as %s' %
                              (url, feed.video_service()))


# -----------------------------------------------------------------------------
# View tests
# -----------------------------------------------------------------------------


class ViewTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['categories', 'feeds', 'videos',
                                        'watched']

    def test_index(self):
        """
        The index view should render the 'localtv/index.html'.  The context
        should include 10 featured videos, 10 popular videos, 10 new views, and
        the base categories (those without parents).
        """
        for watched in Watch.objects.all():
            watched.timestamp = datetime.datetime.now() # so that they're
                                                        # recent
            watched.save()

        c = Client()
        response = c.get(reverse('localtv_index'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/index.html')
        featured = list(Video.objects.get_featured_videos(self.site_settings))
        self.assertEqual(list(response.context['featured_videos']),
                          featured)
        self.assertEqual(list(response.context['popular_videos']),
                          list(Video.objects.get_popular_videos(self.site_settings)))
        self.assertEqual(list(response.context['new_videos']),
                          list(Video.objects.get_latest_videos(self.site_settings)))
        self.assertEqual(list(response.context['comments']), [])

    def test_index_feeds_avoid_frontpage(self):
        """
        Feeds with 'avoid_frontpage' set to True shouldn't be displayed in any
        of the video categories.
        """
        c = Client()
        response = c.get(reverse('localtv_index'))
        new_videos_count = len(response.context['new_videos'])

        Feed.objects.all().update(avoid_frontpage=True)

        response = c.get(reverse('localtv_index'))
        self.assertStatusCodeEquals(response, 200)

        self.assertNotEquals(len(response.context['new_videos']),
                             new_videos_count)

    def test_index_recent_comments_skips_rejected_videos(self):
        """
        Recent comments should only include approved videos.
        """
        unapproved = Video.objects.filter(
            status=Video.UNAPPROVED)[0]
        approved = Video.objects.filter(
            status=Video.ACTIVE)[0]
        rejected = Video.objects.filter(
            status=Video.REJECTED)[0]
        for video in unapproved, approved, rejected:
            Comment.objects.create(
                site=self.site_settings.site,
                content_object=video,
                comment='Test Comment')

        c = Client()
        response = c.get(reverse('localtv_index'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(len(response.context['comments']), 1)
        self.assertEqual(response.context['comments'][0].content_object,
                          approved)

        approved.status = Video.REJECTED
        approved.save()

        c = Client()
        response = c.get(reverse('localtv_index'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(len(response.context['comments']), 0)

    def test_about(self):
        """
        The about view should render the 'localtv/about.html' template.
        """
        c = Client()
        response = c.get(reverse('localtv_about'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/about.html')

    def test_view_video(self):
        """
        The view_video view should render the 'localtv/view_video.html'
        template.  It should include the current video, and a QuerySet of other
        popular videos.
        """
        for watched in Watch.objects.all():
            watched.timestamp = datetime.datetime.now() # so that they're
                                                        # recent
            watched.save()

        video = Video.objects.get(pk=20)

        c = Client()
        response = c.get(video.get_absolute_url())
        self.assertStatusCodeEquals(response, 200)
        self.assertTrue('localtv/view_video.html' in [
                template.name for template in response.templates])
        self.assertEqual(response.context['current_video'], video)
        self.assertEqual(list(response.context['popular_videos']),
                          list(Video.objects.get_popular_videos(
                    self.site_settings)))

    def test_view_video_admins_see_rejected(self):
        """
        The view_video view should return a 404 for rejected videos, unless the
        user is an admin.
        """
        video = Video.objects.get(pk=1)

        c = Client()
        response = c.get(video.get_absolute_url(), follow=True)
        self.assertStatusCodeEquals(response, 404)

        c.login(username='admin', password='admin')
        response = c.get(video.get_absolute_url())
        self.assertStatusCodeEquals(response, 200)

    def test_view_video_slug_redirect(self):
        """
        The view_video view should redirect the user to the URL with the slug
        if the URL doesn't include it or includes the wrong one.
        """
        video = Video.objects.get(pk=20)

        c = Client()
        response = c.get(reverse('localtv_view_video',
                                 args=[20, 'wrong-slug']))
        # 301 is a permanent redirect
        self.assertStatusCodeEquals(response, 301)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver',
                video.get_absolute_url()))

        response = c.get(reverse('localtv_view_video',
                                 args=[20, '']))
        self.assertStatusCodeEquals(response, 301)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver',
                video.get_absolute_url()))

    def test_view_video_category(self):
        """
        If the video has categories, the view_video view should include a
        category in the template and those videos should be shown in place of
        the regular popular videos.
        """
        video = Video.objects.get(pk=20)
        video.categories = [2]
        video.save()

        c = Client()
        response = c.get(video.get_absolute_url())
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.context['category'].pk, 2)
        self.assertEqual(list(response.context['popular_videos']),
                          list(Video.objects.get_popular_videos(
                    self.site_settings).filter(categories__pk=2)))

    def test_view_video_category_referer(self):
        """
        If the view_video referrer was a category page, that category should be
        included in the template and those videos should be shown in place of
        the regular popular videos.
        """
        video = Video.objects.get(pk=20)
        video.categories = [1, 2]
        video.save()

        c = Client()
        response = c.get(video.get_absolute_url(),
                         HTTP_HOST='testserver',
                         HTTP_REFERER='http://%s%s' % (
                'testserver',
                reverse('localtv_category',
                        args=['miro'])))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.context['category'].pk, 1)
        self.assertEqual(list(response.context['popular_videos']),
                          list(Video.objects.get_popular_videos(
                    self.site_settings).filter(categories__pk=1)))

    def assertSearchResults(self, response, expected_sqs,
                            expected_object_count, expected_page_num):
        paginator = response.context['paginator']
        per_page = paginator.per_page
        page_num = response.context['page_obj'].number
        videos = list(response.context['video_list'])
        expected_sqs_results = [r.object for r in expected_sqs if
                                r.object.status == Video.ACTIVE]
        start = (page_num - 1) * per_page
        end = page_num * per_page

        self.assertEqual(page_num, expected_page_num)
        self.assertEqual(len(paginator.object_list),
                          expected_object_count)
        self.assertEqual(videos, expected_sqs_results[start:end])

    def test_video_search(self):
        """
        The video_search view should take a GET['q'] and search through the
        videos.  It should render the
        'localtv/video_listing_search.html' template.
        """
        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'q': 'blender'}) # lots of Blender videos in the test
                                           # data
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/video_listing_search.html')
        self.assertSearchResults(response, 
                                 SearchQuerySet().models(models.Video).filter(
                site=1, content='blender'),
                                 16, 1)

    def test_video_search_phrase(self):
        """
        Phrases in quotes should be searched for as a phrase.
        """
        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'q': '"making of elephants"'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/video_listing_search.html')
        self.assertSearchResults(response,
                                 SearchQuerySet().models(models.Video).filter(
                site=1, content='making of elephants'),
                                 4, 1)

    def test_video_search_no_query(self):
        """
        The video_search view should render the
        'localtv/video_listing_search.html' template.
        """
        c = Client()
        response = c.get(reverse('localtv_search'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/video_listing_search.html')

    def test_video_search_pagination(self):
        """
        The video_search view should take a GET['page'] argument which shows
        the next page of search results.
        """
        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'q': 'blender',
                          'page': 2})

        self.assertStatusCodeEquals(response, 200)
        self.assertSearchResults(response,
                                 SearchQuerySet().models(models.Video).filter(
                site=1, content='blender'),
                                 16, 2)


    def test_video_search_includes_tags(self):
        """
        The video_search view should search the tags for videos.
        """
        video = Video.objects.get(pk=20)
        video.tags = 'tag1 tag2'
        video.save()

        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'q': 'tag1'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(list(response.context['video_list']),
                          [video])

        response = c.get(reverse('localtv_search'),
                          {'q': 'tag2'})
        self.assertEqual(list(response.context['video_list']),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'q': 'tag2 tag1'})
        self.assertEqual(list(response.context['video_list']),
                          [video])

    def test_video_search_includes_categories(self):
        """
        The video_search view should search the category for videos.
        """
        video = Video.objects.get(pk=20)
        video.categories = [2] # Linux (child of Miro)
        video.save()

        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'q': 'Miro'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(list(response.context['video_list']),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'q': 'Linux'})
        self.assertEqual(list(response.context['video_list']),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'q': 'Miro Linux'})
        self.assertEqual(list(response.context['video_list']),
                          [video])

    def test_video_search_includes_user(self):
        """
        The video_search view should search the user who submitted videos.
        """
        video = Video.objects.get(pk=20)
        video.user = User.objects.get(username='superuser')
        video.user.first_name = 'firstname'
        video.user.last_name = 'lastname'
        video.user.save()
        video.save()

        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'q': 'superuser'}) # username
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(list(response.context['video_list']),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'q': 'firstname'}) # first name
        self.assertEqual(list(response.context['video_list']),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'q': 'lastname'}) # last name
        self.assertEqual(list(response.context['video_list']),
                          [video])

    def test_video_search_includes_video_service_user(self):
        """
        The video_search view should search the video service user for videos.
        """
        video = Video.objects.get(pk=20)
        video.video_service_user = 'Video_service_user'
        video.save()

        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'q': 'video_service_user'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(list(response.context['video_list']),
                          [video])

    def test_video_search_includes_feed_name(self):
        """
        The video_search view should search the feed name for videos.
        """
        video = Video.objects.get(pk=20)
        # feed is miropcf

        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'q': 'miropcf'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(list(response.context['video_list']),
                          [video])

    def test_video_search_exclude_terms(self):
        """
        The video_search view should exclude terms that start with - (hyphen).
        """
        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'q': '-blender'})
        self.assertStatusCodeEquals(response, 200)
        self.assertSearchResults(response,
                                 SearchQuerySet().models(models.Video).filter(
                site=1).exclude(content='blender'),
                                 7, 1)

    def test_video_search_unicode(self):
        """
        The video_search view should handle Unicode strings.
        """
        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'q': u'espa\xf1a'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(list(response.context['video_list']), [])

    def test_category_index(self):
        """
        The category_index view should render the
        'localtv/categories.html' template and include the root
        categories (those without parents).
        """
        c = Client()
        response = c.get(reverse('localtv_category_index'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/categories.html')
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(list(response.context['page_obj'].object_list),
                          list(Category.objects.filter(parent=None,
                               site=Site.objects.get_current())))

    def test_category(self):
        """
        The category view should render the 'localtv/category.html'
        template, and include the appropriate category.
        """
        category = Category.objects.get(slug='miro')
        for video in models.Video.objects.filter(status=models.Video.ACTIVE):
            video.categories = [1] # Linux
            video.save()
        c = Client()
        response = c.get(category.get_absolute_url())
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/category.html')
        self.assertEqual(response.context['category'], category)
        videos = list(models.Video.objects.with_best_date().filter(
                status=models.Video.ACTIVE).order_by('-best_date')[:15])
        self.assertEqual(videos, sorted(videos, key=lambda v: v.when(),
                                        reverse=True))
        self.assertEqual(response.context['page_obj'].object_list,
                         videos)

    def test_author_index(self):
        """
        The author_index view should render the
        'localtv/author_list.html' template and include the authors in
        the context.
        """
        c = Client()
        response = c.get(reverse('localtv_author_index'))
        self.assertEqual(response.template[0].name,
                          'localtv/author_list.html')
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(list(response.context['authors']),
                          list(User.objects.all()))

    def test_author(self):
        """
        The author view should render the 'localtv/author.html'
        template and include the author and their videos.
        """
        author = User.objects.get(username='admin')
        c = Client()
        response = c.get(reverse('localtv_author',
                                 args=[author.pk]))
        videos = list(response.context['video_list'])
        site_settings = SiteSettings.objects.get_current()
        expected = list(
            Video.objects.get_latest_videos(site_settings).filter(
                Q(user=author) | Q(authors=author)
            ).distinct().order_by('-best_date')
        )
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/author.html')
        self.assertEqual(response.context['author'], author)
        self.assertEqual(len(videos), 2)
        self.assertEqual(videos, expected)


# -----------------------------------------------------------------------------
# Listing Views tests
# -----------------------------------------------------------------------------


class ListingViewTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['feeds', 'videos', 'watched']

    def test_index(self):
        """
        The listing index view should render the 'localtv/browse.html'
        template.
        """
        c = Client()
        response = c.get(reverse('localtv_list_index'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/browse.html')

    def test_latest_videos(self):
        """
        The new_videos view should render the
        'localtv/video_listing_new.html' template and include the new
        videos.
        """
        c = Client()
        response = c.get(reverse('localtv_list_new'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/video_listing_new.html')
        self.assertEqual(response.context['paginator'].num_pages, 2)
        self.assertEqual(len(response.context['page_obj'].object_list), 15)
        self.assertEqual(list(response.context['page_obj'].object_list),
                          list(Video.objects.get_latest_videos(
                              self.site_settings)[:15]))

    def test_popular_videos(self):
        """
        The popular_videos view should render the
        'localtv/video_listing_popular.html' template and include the
        popular videos.
        """
        for w in Watch.objects.all():
            w.timestamp = datetime.datetime.now()
            w.save()

        c = Client()
        response = c.get(reverse('localtv_list_popular'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/video_listing_popular.html')
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(len(response.context['page_obj'].object_list), 2)
        self.assertEqual(list(response.context['page_obj'].object_list),
                          list(Video.objects.get_popular_videos(
                                 self.site_settings).filter(
                                     watch__timestamp__gte=datetime.datetime.min
                                 ).distinct()))

    def test_featured_videos(self):
        """
        The featured_videos view should render the
        'localtv/video_listing_featured.html' template and include the
        featured videos.
        """
        c = Client()
        response = c.get(reverse('localtv_list_featured'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/video_listing_featured.html')
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(len(response.context['page_obj'].object_list), 2)
        self.assertEqual(list(response.context['page_obj'].object_list),
                          list(Video.objects.filter(status=Video.ACTIVE,
                               last_featured__isnull=False)))

    def test_tag_videos(self):
        """
        The tag_videos view should render the
        'localtv/video_listing_tag.html' template and include the
        tagged videos.
        """
        video = Video.objects.get(pk=20)
        video.tags = 'tag1'
        video.save()

        c = Client()
        response = c.get(reverse('localtv_list_tag',
                         args=['tag1']))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/video_listing_tag.html')
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(len(response.context['page_obj'].object_list), 1)
        self.assertEqual(list(response.context['page_obj'].object_list),
                          [video])

    def test_feed_videos(self):
        """
        The feed_videos view should render the
        'localtv/video_listing_feed.html' template and include the
        videos from the given feed.
        """
        feed = Feed.objects.get(pk=1)

        c = Client()
        response = c.get(reverse('localtv_list_feed',
                                 args=[feed.pk]))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/video_listing_feed.html')
        self.assertEqual(response.context['paginator'].num_pages, 1)
        self.assertEqual(len(response.context['page_obj'].object_list), 1)
        self.assertEqual(list(response.context['page_obj'].object_list),
                          list(feed.video_set.filter(
                    status=Video.ACTIVE)))


# -----------------------------------------------------------------------------
# Comment moderation tests
# -----------------------------------------------------------------------------

class CommentModerationTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['videos']

    def setUp(self):
        BaseTestCase.setUp(self)
        self.old_COMMENTS_APP = getattr(settings, 'COMMENTS_APP', None)
        settings.COMMENTS_APP = 'localtv.comments'
        self.video = Video.objects.get(pk=20)
        self.url = get_form_target()
        if 'captcha' in CommentForm.base_fields:
            del CommentForm.base_fields['captcha']
        self.form = CommentForm(self.video,
                                initial={
                'name': 'postname',
                'email': 'post@email.com',
                'url': 'http://posturl.com/'})
        self.POST_data = self.form.initial
        self.POST_data['comment'] = 'comment string'

    def tearDown(self):
        settings.COMMENTS_APP = self.old_COMMENTS_APP

    def test_deleting_video_deletes_comments(self):
        """
        If the video for a comment is deleted, the comment should be deleted as
        well.
        """
        c = Client()
        c.post(self.url, self.POST_data)
        self.assertEqual(Comment.objects.count(), 1)
        self.video.delete()
        self.assertFalse(Comment.objects.exists())

    def test_comment_does_not_require_email_or_url(self):
        """
        Posting a comment should not require an e-mail address or URL.
        """
        del self.POST_data['email']
        del self.POST_data['url']

        c = Client()
        c.post(self.url, self.POST_data)
        comment = Comment.objects.get()
        self.assertEqual(comment.content_object, self.video)
        self.assertFalse(comment.is_public)
        self.assertEqual(comment.name, 'postname')
        self.assertEqual(comment.email, '')
        self.assertEqual(comment.url, '')

    def test_screen_all_comments_False(self):
        """
        If SiteSettings.screen_all_comments is False, the comment should be
        saved and marked as public.
        """
        self.site_settings.screen_all_comments = False
        self.site_settings.save()

        c = Client()
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEqual(comment.content_object, self.video)
        self.assertTrue(comment.is_public)
        self.assertEqual(comment.name, 'postname')
        self.assertEqual(comment.email, 'post@email.com')
        self.assertEqual(comment.url, 'http://posturl.com/')

    def test_screen_all_comments_True(self):
        """
        If SiteSettings.screen_all_comments is True, the comment should be
        moderated (not public).
        """
        notice_type = notification.NoticeType.objects.get(
            label='admin_new_comment')
        for username in 'admin', 'superuser':
            user = User.objects.get(username=username)
            setting = notification.get_notification_setting(user, notice_type,
                                                            "1")
            setting.send = True
            setting.save()

        c = Client()
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEqual(comment.content_object, self.video)
        self.assertFalse(comment.is_public)
        self.assertEqual(comment.name, 'postname')
        self.assertEqual(comment.email, 'post@email.com')
        self.assertEqual(comment.url, 'http://posturl.com/')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(),
                          ['admin@testserver.local',
                           'superuser@testserver.local'])

    def test_screen_all_comments_True_admin(self):
        """
        Even if SiteSettings,screen_all_comments is True, comments from logged
        in admins should not be screened.
        """
        c = Client()
        c.login(username='admin', password='admin')
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEqual(comment.content_object, self.video)
        self.assertTrue(comment.is_public)
        comment.delete()

        c.login(username='superuser', password='superuser')
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEqual(comment.content_object, self.video)
        self.assertTrue(comment.is_public)

    def test_comments_email_admins_False(self):
        """
        If no admin is subscribed to the 'admin_new_comment' notification, no
        e-mail should be sent when a comment is made.
        """
        c = Client()
        c.post(self.url, self.POST_data)

        self.assertEqual(mail.outbox, [])

    def test_comments_email_admins_True(self):
        """
        If any admins are subscribed to the 'admin_new_comment' notification,
        an e-mail should be sent when a comment is made to each.
        """
        notice_type = notification.NoticeType.objects.get(
            label='admin_new_comment')
        for username in 'admin', 'superuser':
            user = User.objects.get(username=username)
            setting = notification.get_notification_setting(user, notice_type,
                                                            "1")
            setting.send = True
            setting.save()

        c = Client()
        c.post(self.url, self.POST_data)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(),
                          ['admin@testserver.local',
                           'superuser@testserver.local'])

    def test_comments_required_login_False(self):
        """
        If SiteSettings.comments_required_login is False, comments should be
        allowed by any user.  This is the same test code as
        test_screen_all_comments_False().
        """
        c = Client()
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEqual(comment.content_object, self.video)
        self.assertFalse(comment.is_public)
        self.assertEqual(comment.name, 'postname')
        self.assertEqual(comment.email, 'post@email.com')
        self.assertEqual(comment.url, 'http://posturl.com/')

    def test_comments_required_login_True(self):
        """
        If SiteSettings.comments_required_login, making a comment should
        require a logged-in user.
        """
        self.site_settings.comments_required_login = True
        self.site_settings.save()

        c = Client()
        response = c.post(self.url, self.POST_data)
        self.assertStatusCodeEquals(response, 400)
        self.assertEqual(Comment.objects.count(), 0)

        c.login(username='user', password='password')
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEqual(comment.content_object, self.video)
        self.assertFalse(comment.is_public)
        self.assertEqual(comment.name, 'Firstname Lastname')
        self.assertEqual(comment.email, 'user@testserver.local')
        self.assertEqual(comment.url, 'http://posturl.com/')

    def test_comments_email_submitter(self):
        """
        If the submitter of a video has the 'video_comment' notificiation
        enabled, an e-mail with the comment should be sent to them.
        """
        video = Video.objects.get(pk=43) # has a user
        form = CommentForm(video,
                           initial={
                'name': 'postname',
                'email': 'post@email.com',
                'url': 'http://posturl.com/'})
        POST_data = form.initial
        POST_data['comment'] = 'comment string'

        # the default is to receive comment e-mails

        self.site_settings.screen_all_comments = False
        self.site_settings.save()

        c = Client()
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(),
                          [video.user.email])

    def test_comments_email_submitter_once(self):
        """
        If the submitter of a video is an admin and has both the
        'video_comment' and 'admin_new_comment' notifications, they should only
        receive one e-mail.
        """
        admin = User.objects.get(username='admin')

        notice_type = notification.NoticeType.objects.get(
            label='admin_new_comment')
        setting = notification.get_notification_setting(admin, notice_type,
                                                        "1")
        setting.send = True
        setting.save()

        self.video.user = admin
        self.video.save()

        # the default is to receive comment e-mails

        self.site_settings.screen_all_comments = False
        self.site_settings.save()

        c = Client()
        c.post(self.url, self.POST_data)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(),
                          [admin.email])

    def test_comments_email_previous_commenter(self):
        """
        If previous comment submitters have the 'comment_post_comment'
        notification enabled, they should get an e-mail when a new comment
        appears on a video they've commented on.
        """
        user = User.objects.get(username='user')

        self.video.user = None
        self.video.save()

        self.site_settings.screen_all_comments = False
        self.site_settings.save()

        c = Client()
        c.login(username='user', password='password')
        self.assertStatusCodeEquals(c.post(self.url, self.POST_data), 302)

        self.assertEqual(len(mail.outbox), 0)

        mail.outbox = []

        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data['comment'] = 'another comment'
        self.assertStatusCodeEquals(c.post(self.url, self.POST_data), 302)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(),
                          [user.email])


# -----------------------------------------------------------------------------
# Video model tests
# -----------------------------------------------------------------------------

class VideoModelTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['videos']

    def test_when(self):
        """
        Video.when() returns the best available date for the video:

        1) when_published (original publish date)
        2) when_approved (when it was made visible on the site)
        3) when_submitted (when it was submitted to the site)
        """
        v = Video.objects.get(pk=11)
        self.assertEqual(v.when(), v.when_published)
        v.when_published = None
        self.assertEqual(v.when(), v.when_approved)
        v.when_approved = None
        self.assertEqual(v.when(), v.when_submitted)

    def test_when_use_original_date_False(self):
        """
        When SiteSettings.use_original_date is False, Video.when() ignores the
        when_published date.
        """
        self.site_settings.use_original_date = False
        self.site_settings.save()
        v = Video.objects.get(pk=11)
        self.assertEqual(v.when(), v.when_approved)


    def test_when_prefix(self):
        """
        Video.when_prefix() returns 'published' if the date is
        when_published, otherwise it returns 'posted'..
        """
        v = Video.objects.get(pk=11)
        self.assertEqual(v.when_prefix(), 'published')
        v.when_published = None
        self.assertEqual(v.when_prefix(), 'posted')

    def test_when_prefix_use_original_date_False(self):
        """
        When SiteSettings.use_original_date is False, Video.when_prefix()
        returns 'posted'.
        """
        self.site_settings.use_original_date = False
        self.site_settings.save()
        v = Video.objects.get(pk=11)
        self.assertEqual(v.when_prefix(), 'posted')

    def test_latest(self):
        """
        Video.objects.get_latest_videos() should return a QuerySet ordered by
        the best available date:

        1) when_published
        2) when_approved
        3) when_submitted

        SearchQuerySet().models(Video).order_by('-best_date_with_published')
        should return the same videos.

        """
        expected_pks = set(Video.objects.filter(status=Video.ACTIVE,
                                                site=self.site_settings.site
                                       ).values_list('pk', flat=True))

        results = list(Video.objects.get_latest_videos(self.site_settings))
        self.assertEqual(set(r.pk for r in results), expected_pks)
        for i in xrange(len(results) - 1):
            self.assertTrue(results[i].when() >= results[i+1].when())

        sqs = SearchQuerySet().models(Video).order_by(
                                      '-best_date_with_published')
        results = list([r.object for r in sqs.load_all()])
        self.assertEqual(set(r.pk for r in results), expected_pks)
        for i in xrange(len(results) - 1):
            self.assertTrue(results[i].when() >= results[i+1].when())

    def test_latest_use_original_date_False(self):
        """
        When SiteSettings.use_original_date is False,
        Video.objects.get_latest_videos() should ignore the when_published date.

        SearchQuerySet().models(Video).order_by('-best_date') should return the
        same videos.

        """
        expected_pks = set(Video.objects.filter(status=Video.ACTIVE,
                                                site=self.site_settings.site
                                       ).values_list('pk', flat=True))

        self.site_settings.use_original_date = False
        self.site_settings.save()

        results = list(Video.objects.get_latest_videos(self.site_settings))
        self.assertEqual(set(r.pk for r in results), expected_pks)
        for i in xrange(len(results) - 1):
            self.assertTrue(results[i].when() >= results[i+1].when())

        sqs = SearchQuerySet().models(Video).order_by(
                                      '-best_date')
        results = list([r.object for r in sqs.load_all()])
        self.assertEqual(set(r.pk for r in results), expected_pks)
        for i in xrange(len(results) - 1):
            self.assertTrue(results[i].when() >= results[i+1].when())

    def test_thumbnail_404(self):
        """
        If a Video has a thumbnail that returns a 404, no error should be
        raised, and `has_thumbnail` should be set to False.
        """
        v = Video.objects.get(pk=11)
        v.thumbnail_url = 'http://pculture.org/doesnotexist'
        v.has_thumbnail = True
        v.save_thumbnail()
        self.assertFalse(v.has_thumbnail)

    def test_thumbnail_deleted(self):
        """
        If a Video has a thumbnail, deleting the Video should remove the
        thumbnail.
        """
        v = Video.objects.get(pk=11)
        v.save_thumbnail_from_file(File(file(self._data_file('logo.png'))))

        paths = [v.get_original_thumb_storage_path()]
        for size in Video.THUMB_SIZES:
            paths.append(v.get_resized_thumb_storage_path(*size))

        v.delete()
        for path in paths:
            self.assertFalse(storage.default_storage.exists(path),
                             '%s was not deleted' % path)

    def test_original_video_created(self):
        """
        When an Video object is a created, an OriginalVideo object should also
        be created with the data from that video.
        """
        v = Video.objects.create(
            site=self.site_settings.site,
            name='Test Name',
            description='Test Description',
            website_url='http://www.youtube.com/'
            )
        v.tags = 'foo bar "baz bum"'
        self.assertFalse(v.original is None)
        self.assertEqual(v.original.name, v.name)
        self.assertEqual(v.original.description, v.description)
        self.assertTrue(v.original.thumbnail_updated -
                        datetime.datetime.now() <
                        datetime.timedelta(seconds=15))
        self.assertEqual(set(v.tags), set(Tag.objects.filter(
                    name__in=('foo', 'bar', 'baz bum'))))

    def test_no_original_video_without_website_url(self):
        """
        If we don't know have a website URL for the video, don't bother
        creating an OriginalVideo object.
        """
        v = Video.objects.create(
            site=self.site_settings.site,
            name='Test Name',
            description='Test Description',
            )
        self.assertRaises(OriginalVideo.DoesNotExist,
                          lambda: v.original)

# -----------------------------------------------------------------------------
# Site tier tests
# -----------------------------------------------------------------------------
class SiteTierTests(BaseTestCase):
    def test_basic_account(self):
        # Create a SiteSettings whose site_tier is set to 'basic'
        self.site_settings.tier_name = 'basic'
        self.site_settings.save()
        tier = self.site_settings.get_tier()
        self.assertEqual(0, tier.dollar_cost())
        self.assertEqual(500, tier.videos_limit())
        self.assertEqual(1, tier.admins_limit())
        self.assertFalse(tier.permit_custom_css())
        self.assertFalse(tier.permit_custom_template())

    def test_plus_account(self):
        # Create a SiteSettings whose site_tier is set to 'plus'
        self.site_settings.tier_name = 'plus'
        self.site_settings.save()
        tier = self.site_settings.get_tier()
        self.assertEqual(PLUS_COST, tier.dollar_cost())
        self.assertEqual(1000, tier.videos_limit())
        self.assertEqual(5, tier.admins_limit())
        self.assertTrue(tier.permit_custom_css())
        self.assertFalse(tier.permit_custom_template())

    def test_premium_account(self):
        # Create a SiteSettings whose site_tier is set to 'premium'
        self.site_settings.tier_name = 'premium'
        self.site_settings.save()
        tier = self.site_settings.get_tier()
        self.assertEqual(PREMIUM_COST, tier.dollar_cost())
        self.assertEqual(5000, tier.videos_limit())
        self.assertEqual(None, tier.admins_limit())
        self.assertTrue(tier.permit_custom_css())
        self.assertFalse(tier.permit_custom_template())

    def test_max_account(self):
        self.site_settings.tier_name = 'max'
        self.site_settings.save()
        tier = self.site_settings.get_tier()
        self.assertEqual(MAX_COST, tier.dollar_cost())
        self.assertEqual(25000, tier.videos_limit())
        self.assertEqual(None, tier.admins_limit())
        self.assertTrue(tier.permit_custom_css())
        self.assertTrue(tier.permit_custom_template())

# -----------------------------------------------------------------------------
# Watch model tests
# -----------------------------------------------------------------------------

class WatchModelTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['videos']

    def test_add(self):
        """
        Watch.add(request, video) should add a Watch object to the database for
        the given video.
        """
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = '123.123.123.123'
        request.user = User.objects.get(username='user')

        video = Video.objects.get(pk=1)

        Watch.add(request, video)

        watch = Watch.objects.get()
        self.assertEqual(watch.video, video)
        self.assertTrue(watch.timestamp - datetime.datetime.now() <
                        datetime.timedelta(seconds=1))
        self.assertEqual(watch.user, request.user)
        self.assertEqual(watch.ip_address, request.META['REMOTE_ADDR'])

    def test_add_unauthenticated(self):
        """
        Unauthenticated requests should add a Watch object with user set to
        None.
        """
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = '123.123.123.123'

        video = Video.objects.get(pk=1)

        Watch.add(request, video)

        watch = Watch.objects.get()
        self.assertEqual(watch.video, video)
        self.assertTrue(watch.timestamp - datetime.datetime.now() <
                        datetime.timedelta(seconds=1))
        self.assertEqual(watch.user, None)
        self.assertEqual(watch.ip_address, request.META['REMOTE_ADDR'])

    def test_add_invalid_ip(self):
        """
        Requests with an invalid IP address should not raise an error.  The IP
        address should be saved as 0.0.0.0.
        """
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = 'unknown'

        video = Video.objects.get(pk=1)

        Watch.add(request, video)

        w = Watch.objects.get()
        self.assertEqual(w.video, video)
        self.assertEqual(w.ip_address, '0.0.0.0')

    def test_add_robot(self):
        """
        Requests from Robots (Googlebot, Baiduspider, &c) shouldn't count as
        watches.
        """
        request = HttpRequest()
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 Googlebot'

        video = Video.objects.get(pk=1)

        Watch.add(request, video)

        request = HttpRequest()
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 BaiduSpider'

        Watch.add(request, video)

        self.assertEqual(Watch.objects.count(), 0)



# -----------------------------------------------------------------------------
# SavedSearch model tests
# -----------------------------------------------------------------------------

class SavedSearchImportTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['savedsearches']

    def test_update(self):
        """
        SavedSearch.update() should create new Video objects linked to
        the search.
        """
        ss = SavedSearch.objects.get(pk=1)
        self.assertEqual(ss.video_set.count(), 0)
        ss.update()
        self.assertNotEquals(ss.video_set.count(), 0)

    def test_update_ignore_duplicates(self):
        """
        A search that includes the same video should should not add the video a
        second time.
        """
        ss = SavedSearch.objects.get(pk=1)
        ss.update()
        count = ss.video_set.count()
        ss.update()
        self.assertEqual(ss.video_set.count(), count)

    def test_attribution_auto(self):
        """
        If a SavedSearch has authors set, imported videos should be given that
        authorship.
        """
        ss = SavedSearch.objects.get(pk=1)
        ss.auto_authors = [User.objects.get(pk=1)]
        ss.update()
        video = ss.video_set.all()[0]
        self.assertEqual(list(ss.auto_authors.all()),
                          list(video.authors.all()))

    def test_attribution_default(self):
        """
        If a SavedSearch has no author, imported videos should have a User
        based on the user on the original video service.
        """
        ss = SavedSearch.objects.get(pk=1)
        self.assertFalse(ss.auto_authors.all().exists())
        ss.update()
        video = ss.video_set.all()[0]
        self.assertTrue(video.authors.all().exists())

class OriginalVideoModelTestCase(BaseTestCase):

    BASE_URL = 'http://blip.tv/file/1077145/' # Miro sponsors
    BASE_DATA = {
        'name': u'Miro appreciates the support of our sponsors',
        'description': u"""<p>Miro is a non-profit project working \
to build a better media future as television moves online. We provide our \
software free to our users and other developers, despite the significant cost \
of developing the software. This work is made possible in part by the support \
of our sponsors. Please watch this video for a message from our sponsors. If \
you wish to support Miro yourself, please donate $10 today.</p>""",
        'thumbnail_url': ('http://a.images.blip.tv/Mirosponsorship-'
            'MiroAppreciatesTheSupportOfOurSponsors478.png'),
        # it seems like thumbnails are updated on the 8th of each month; this
        # code should get the last 8th that happened.  Just replacing today's
        # date with an 8 doesn't work early in the month, so backtrack a bit
        # first.
        'thumbnail_updated': (datetime.datetime.now() -
                              datetime.timedelta(days=8)).replace(day=8),
        }


    def setUp(self):
        self.maxDiff = None
        BaseTestCase.setUp(self)
        self.video = Video.objects.create(
            site=self.site_settings.site,
            website_url=self.BASE_URL,
            name=self.BASE_DATA['name'],
            description=self.BASE_DATA['description'],
            thumbnail_url=self.BASE_DATA['thumbnail_url'])
        self.original = self.video.original
        self.original.thumbnail_updated = self.BASE_DATA['thumbnail_updated']
        self.original.save()
        notice_type = notification.NoticeType.objects.get(
            label='admin_video_updated')
        for username in 'admin', 'superuser':
            user = User.objects.get(username=username)
            setting = notification.get_notification_setting(user, notice_type,
                                                            "1")
            setting.send = True
            setting.save()

    def test_normalize_newlines_backslash_r(self):
        dos_style = 'hello\r\nthere'
        unix_style = 'hello\nthere'
        self.assertEqual(
            utils.normalize_newlines(dos_style),
            utils.normalize_newlines(unix_style))

    def test_normalize_newlines_weird_input(self):
        self.assertTrue(utils.normalize_newlines(None)
                     is None)
        self.assertTrue(utils.normalize_newlines(True) is True)

    def test_no_changes(self):
        """
        If nothing has changed, then OriginalVideo.changed_fields() should
        return an empty dictionary.
        """
        self.assertEqual(self.original.changed_fields(), {})

    def assertChanges(self, field, value, old_value):
        """
        Sets the field on self.original, tests that
        self.original.changed_fields() contains the correct data, and then
        resets the field.
        """
        setattr(self.original, field, value)
        changed_fields = self.original.changed_fields()
        self.assertEqual(changed_fields, {field: old_value})
        setattr(self.original, field, old_value)

    def test_name_change(self):
        """
        If the name has changed, OriginalVideo.changed_fields() should return
        the new name.
        """
        self.assertChanges('name', 'Different Name', self.BASE_DATA['name'])

    def test_description_change(self):
        """
        If the description has changed, OriginalVideo.changed_fields() should
        return the new description.
        """
        self.assertChanges('description', 'Different Description',
                           self.BASE_DATA['description'])

    def test_tags_change(self):
        """
        If the tags have changed, OriginalVideo.changed_fields() should return
        the new tags.
        """
        self.assertChanges('tags', ['Different', 'Tags'], set())

    def test_thumbnail_url_change(self):
        """
        If the thumbnail_url has changed, OriginalVideo.changed_fields() should
        return the new thumbnail_url.
        """
        self.assertChanges('thumbnail_url',
            'http://www.google.com/intl/en_ALL/images/srpr/logo1w.png',
            self.BASE_DATA['thumbnail_url'])

    def test_thumbnail_updated_change(self):
        """
        If the date on the thumbnail has changed,
        OriginalVideo.changed_fields() should return the new thumbnail date.
        """
        old_hash = self.original.remote_thumbnail_hash
        old_updated = self.original.thumbnail_updated
        self.original.remote_thumbnail_hash = '6a63e0b2a8c085c06b1777aa62af98bde5db1197'
        self.original.thumbnail_updated = datetime.datetime.min

        time_at_start_of_test = datetime.datetime.utcnow()
        changed_fields = self.original.changed_fields()
        self.assertTrue('thumbnail_updated' in changed_fields)
        new_thumbnail_timestamp = changed_fields['thumbnail_updated']
        self.assertTrue(new_thumbnail_timestamp >=
                        time_at_start_of_test)
        self.original.remote_thumbnail_hash = old_hash
        self.original.thumbnail_updated = old_updated

    def test_thumbnail_change_ignored_if_hash_matches(self):
        old_updated = self.original.thumbnail_updated
        self.original.thumbnail_updated = datetime.datetime.min
        self.original.remote_thumbnail_hash = '6a63e0b2a8c085c06b1777aa62af98bde5db1196'

        changed_fields = self.original.changed_fields()
        self.assertFalse('thumbnail_updated' in changed_fields)
        self.original.thumbnail_updated = old_updated

    def test_update_no_updates(self):
        """
        If nothing has been updated, OriginalVideo.update() should not send any
        e-mails.
        """
        self.original.update()
        self.assertEqual(len(mail.outbox), 0)

    def test_update_modified(self):
        """
        If there have been updates to a modified video, send an e-mail to
        anyone with the 'admin_video_updated' notification option.  It should
        also update the OriginalVideo object to the current data.
        """
        self.original.name = 'Different Name'
        self.original.thumbnail_url = \
            'http://www.google.com/intl/en_ALL/images/srpr/logo1w.png'
        self.original.tags = 'foo bar'
        self.original.save()

        self.original.update()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(),
                          ['admin@testserver.local',
                           'superuser@testserver.local'])
        original = OriginalVideo.objects.get(pk=self.original.pk)
        self.assertEqual(original.name,
                          self.BASE_DATA['name'])
        self.assertEqual(original.thumbnail_url,
                          self.BASE_DATA['thumbnail_url'])
        self.assertEqual(set(tag.name for tag in original.tags),
                          set())
        self.assertEqual(original.video.thumbnail_url,
                          self.video.thumbnail_url) # didn't change
        self.assertEqual(set(original.video.tags),
                          set(self.video.tags))

    def test_update_unmodified(self):
        """
        If there have been updates to an unmodified video, no e-mail should be
        sent; the video should simply be changed.
        """
        self.video.name = self.original.name = 'Different Name'
        self.video.thumbnail_url = self.original.thumbnail_url = \
            'http://www.google.com/intl/en_ALL/images/srpr/logo1w.png'
        self.video.tags = self.original.tags = 'foo bar'
        self.video.save()
        self.original.save()

        self.original.update()


        self.assertEqual(len(mail.outbox), 0)
        original = OriginalVideo.objects.get(pk=self.original.pk)
        self.assertEqual(original.name,
                          self.BASE_DATA['name'])
        self.assertEqual(original.thumbnail_url,
                          self.BASE_DATA['thumbnail_url'])
        self.assertEqual(set(tag.name for tag in original.tags),
                          set())
        self.assertEqual(original.video.name,
                          original.name)
        self.assertEqual(original.video.thumbnail_url,
                          original.thumbnail_url)
        self.assertEqual(set(original.video.tags),
                          set(original.tags))

    def test_update_both(self):
        """
        If there are some fields that are modified in the video, and others
        that aren't, the modified fields should have an e-mail sent and the
        other should just be modified.
        """
        self.video.name = self.original.name = 'Different Name'
        self.original.description = 'Different Description'
        self.video.thumbnail_url = self.original.thumbnail_url = \
            'http://www.google.com/intl/en_ALL/images/srpr/logo1w.png'
        self.video.tags = self.original.tags = 'foo bar'
        self.video.save()
        self.original.save()

        self.original.update()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(),
                          ['admin@testserver.local',
                           'superuser@testserver.local'])
        original = OriginalVideo.objects.get(pk=self.original.pk)
        self.assertEqual(original.name,
                          self.BASE_DATA['name'])
        self.assertEqual(original.thumbnail_url,
                          self.BASE_DATA['thumbnail_url'])
        self.assertEqual(set(original.tags),
                          set())
        self.assertEqual(original.video.name,
                          original.name)
        self.assertEqual(original.video.thumbnail_url,
                          original.thumbnail_url)
        self.assertEqual(set(original.video.tags),
                          set(original.tags))

    def test_remote_video_deletion(self):
        """
        If the remote video is deleted, send a special message along those
        lines (rather than crash).
        """
        # For vimeo, at least, this is what remote video deletion looks like:
        vidscraper_result = vidscraper.Video(self.BASE_URL) # all fields None

        self.original.update(override_vidscraper_result=vidscraper_result)

        self.assertTrue(self.original.remote_video_was_deleted)
        self.assertEqual(len(mail.outbox), 0) # not e-mailed yet

        # second try sends the e-mail
        self.original.update(override_vidscraper_result=vidscraper_result)

        self.assertTrue(self.original.remote_video_was_deleted)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(),
                          ['admin@testserver.local',
                           'superuser@testserver.local'])
        self.assertTrue(u'Deleted' in unicode(mail.outbox[0].message()))
        # Now, imagine a day goes by.
        # Clear the outbox, and do the same query again.
        mail.outbox = []
        self.original.update(override_vidscraper_result=vidscraper_result)
        self.assertEqual(len(mail.outbox), 0)

    def test_remote_video_spurious_delete(self):
        """
        If the remote video pretends to be deleted, then don't send an e-mail
        and reset the remote_video_was_deleted flag.
        """
        # For vimeo, at least, this is what remote video deletion looks like:
        vidscraper_result = vidscraper.Video(self.BASE_URL)

        self.original.update(override_vidscraper_result=vidscraper_result)

        self.assertTrue(self.original.remote_video_was_deleted)
        self.assertEqual(len(mail.outbox), 0) # not e-mailed yet

        # second try doesn't sends the e-mail
        vidscraper_result.__dict__.update({
                'title': self.video.name,
                'description': self.video.description,
                'tags': list(self.video.tags),
                'thumbnail_url': self.video.thumbnail_url})

        self.original.update(override_vidscraper_result=vidscraper_result)

        self.assertFalse(self.original.remote_video_was_deleted)
        self.assertEqual(len(mail.outbox), 0)

    def test_remote_video_newline_fiddling(self):
        """
        YouTube's descriptions sometimes come back with \r\n as the line
        ending, and sometimes with \n.

        When comparing descriptions that are the same except for that, consider
        them equivalent.
        """
        # Set up the Original Video to have the \n-based line breaks
        self.original.description = 'Something with some\nline breaks'
        self.original.save()

        # and set up the user's modified video to have a totally different description
        self.original.video.description = 'Something chosen by the user'
        self.original.video.save()

        # Now, do a refresh, simulating the remote response having \r\n line endings
        vidscraper_result = vidscraper.Video(self.BASE_URL)
        vidscraper_result.__dict__.update(
            {'description': self.original.description.replace('\n', '\r\n'),
             'thumbnail_url': self.BASE_DATA['thumbnail_url'],
             'title': self.BASE_DATA['name'],
             })
        changes = self.original.changed_fields(override_vidscraper_result=vidscraper_result)
        self.assertFalse(changes)

class TestWmodeFilter(BaseTestCase):
    def test_add_transparent_wmode_to_object(self):
        input = "<object></object>"
        output = '<object><param name="wmode" value="transparent"></object>'
        self.assertEqual(output,
                         localtv.templatetags.filters.wmode_transparent(input))

    def test_add_transparent_wmode_to_two_objects(self):
        input = "<object></object>"
        output = '<object><param name="wmode" value="transparent"></object>'
        self.assertEqual(output + output,
                         localtv.templatetags.filters.wmode_transparent(input + input))

    def test_add_transparent_wmode_to_embed(self):
        input = '<embed type="application/x-shockwave-flash"></embed>'
        output = '<embed type="application/x-shockwave-flash" wmode="transparent"></embed>'
        self.assertEqual(output,
                         localtv.templatetags.filters.wmode_transparent(input))
                
class SiteSettingsEnablesRestrictionsAfterPayment(BaseTestCase):
    def test_unit(self):
        self.assertFalse(SiteSettings.enforce_tiers(override_setting=True))
        tier_info = TierInfo.objects.get_current()
        tier_info.user_has_successfully_performed_a_paypal_transaction = True
        tier_info.save()
        self.assertTrue(SiteSettings.enforce_tiers(override_setting=True))

class TierMethodsTests(BaseTestCase):

    @mock.patch('localtv.models.SiteSettings.enforce_tiers', mock.Mock(return_value=False))
    @mock.patch('localtv.tiers.Tier.remaining_videos', mock.Mock(return_value=0))
    def test_can_add_more_videos(self):
        # This is true because enforcement is off.
        self.assertTrue(localtv.tiers.Tier.get().can_add_more_videos())

    @mock.patch('localtv.models.SiteSettings.enforce_tiers', mock.Mock(return_value=True))
    @mock.patch('localtv.tiers.Tier.remaining_videos', mock.Mock(return_value=0))
    def test_can_add_more_videos_returns_false(self):
        # This is False because the number of videos remaining is zero.
        self.assertFalse(localtv.tiers.Tier.get().can_add_more_videos())

    @mock.patch('localtv.models.SiteSettings.enforce_tiers', mock.Mock(return_value=True))
    @mock.patch('localtv.tiers.Tier.remaining_videos', mock.Mock(return_value=1))
    def test_can_add_video_lets_you_add_final_video(self):
        # This is False because the number of videos remaining is zero.
        self.assertTrue(localtv.tiers.Tier.get().can_add_more_videos())

    def test_time_until_free_trial_expires_none_when_not_in_free_trial(self):
        ti = TierInfo.objects.get_current()
        ti.in_free_trial = False
        ti.save()
        self.assertEqual(None, ti.time_until_free_trial_expires())

    def test_time_until_free_trial_expires_none_when_no_payment_due(self):
        ti = TierInfo.objects.get_current()
        ti.in_free_trial = True
        ti.payment_due_date = None # Note that this is a kind of insane state.
        ti.save()
        self.assertEqual(None, ti.time_until_free_trial_expires())

    def test_time_until_free_trial_expires(self):
        now = datetime.datetime(2011, 5, 24, 23, 44, 30)
        a_bit_in_the_future = now + datetime.timedelta(hours=5)
        ti = TierInfo.objects.get_current()
        ti.in_free_trial = True
        ti.payment_due_date = a_bit_in_the_future
        ti.save()
        self.assertEqual(datetime.timedelta(hours=5),
                         ti.time_until_free_trial_expires(now=now))

class LegacyFeedViewTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['videos', 'categories', 'feeds']

    def test_feed_views_respect_count_when_set(self):
        fake_request = self.factory.get('?count=10')
        feed = localtv.feeds.views.NewVideosFeed(json=False)
        obj = feed.get_object(fake_request)
        self.assertEqual(10, len(feed.items(obj)))

    def test_feed_views_ignore_count_when_nonsense(self):
        fake_request = self.factory.get('?count=nonsense')
        feed = localtv.feeds.views.NewVideosFeed(json=False)
        obj = feed.get_object(fake_request)
        # 23, because that's the number of videos in the fixture
        self.assertEqual(23, len(feed.items(obj)))

    def test_feed_views_ignore_count_when_empty(self):
        fake_request = self.factory.get('')
        feed = localtv.feeds.views.NewVideosFeed(json=False)
        obj = feed.get_object(fake_request)
        # 23, because that's the number of videos in the fixture
        self.assertEqual(23, len(feed.items(obj)))

    def test_category_feed_renders_at_all(self):
        fake_request = self.factory.get('?count=10')
        view = localtv.feeds.views.CategoryVideosFeed()
        response = view(fake_request, slug='linux')
        self.assertEqual(200, response.status_code)

    def test_feed_views_respect_count_when_set_integration(self):
        # Put 3 videos into the Linux category
        linux_category = Category.objects.get(slug='linux')
        three_vids = Video.objects.get_latest_videos(
            self.site_settings)[:3]
        self.assertEqual(len(three_vids), 3)
        for vid in three_vids:
            vid.categories.add(linux_category)
            vid.status = Video.ACTIVE
            vid.save()
        self.assertEqual(linux_category.approved_set.count(), 3)
        # Do a GET for the first 2 in the feed
        fake_request = self.factory.get('?count=2')
        view = localtv.feeds.views.CategoryVideosFeed()
        response = view(fake_request, slug='linux')
        self.assertEqual(200, response.status_code)
        parsed = feedparser.parse(response.content)
        items_from_first_GET = parsed['items']
        self.assertEqual(2, len(items_from_first_GET))

        # Do a GET for the next "2" (just 1 left)
        fake_request = self.factory.get('?count=2&start-index=2')
        view = localtv.feeds.views.CategoryVideosFeed()
        response = view(fake_request, slug='linux')
        self.assertEqual(200, response.status_code)
        parsed = feedparser.parse(response.content)
        items_from_second_GET = parsed['items']
        self.assertEqual(1, len(items_from_second_GET))

if localtv.settings.voting_enabled():
    from voting.models import Vote

    class VotingTestCase(BaseTestCase):

        fixtures = BaseTestCase.fixtures + ['videos', 'categories', 'feeds']

        def setUp(self):
            BaseTestCase.setUp(self)
            self.video = Video.objects.get(pk=20)
            self.category = Category.objects.get(slug='miro')
            self.category.contest_mode = datetime.datetime.now()
            self.category.save()
            self.video.categories.add(self.category)

        def test_voting_view_add(self):
            """
            A POST request to the localtv_video_vote should add a vote for that
            video ID.
            """
            c = Client()
            c.login(username='user', password='password')
            response = c.post(reverse('localtv_video_vote',
                                      args=(self.video.pk,
                                            'up')))
            self.assertStatusCodeEquals(response, 302)
            self.assertEqual(response['Location'],
                             'http://testserver%s' % (
                    self.video.get_absolute_url()))
            self.assertEqual(
                Vote.objects.count(),
                1)
            vote = Vote.objects.get()
            self.assertEqual(vote.object, self.video)
            self.assertEqual(vote.user.username, 'user')
            self.assertEqual(vote.vote, 1)

        def test_voting_view_add_twice(self):
            """
            Adding a vote multiple times doesn't create multiple votes.
            """
            c = Client()
            c.login(username='user', password='password')
            c.post(reverse('localtv_video_vote',
                                      args=(self.video.pk,
                                            'up')))
            c.post(reverse('localtv_video_vote',
                                      args=(self.video.pk,
                                            'up')))
            self.assertEqual(
                Vote.objects.count(),
                1)

        def test_voting_view_clear(self):
            """
            Clearing a vote removes it from the database.
            """
            c = Client()
            c.login(username='user', password='password')
            c.post(reverse('localtv_video_vote',
                                      args=(self.video.pk,
                                            'up')))
            self.assertEqual(
                Vote.objects.count(),
                1)
            c.post(reverse('localtv_video_vote',
                           args=(self.video.pk,
                                 'clear')))
            self.assertEqual(
                Vote.objects.count(),
                0)

        def test_voting_view_too_many_votes(self):
            """
            You should only be able to vote for 3 videos in a category.
            """
            videos = []
            for v in Video.objects.all()[:4]:
                v.categories.add(self.category)
                videos.append(v)

            c = Client()
            c.login(username='user', password='password')

            for video in videos:
                c.post(reverse('localtv_video_vote',
                               args=(video.pk,
                                     'up')))

            self.assertEqual(
                Vote.objects.count(),
                3)

            self.assertEqual(
                set(
                    Vote.objects.values_list(
                        'object_id', flat=True)),
                set([v.pk for v in videos[:3]]))

        def test_voting_view_clear_with_too_many(self):
            """
            Even if the user has voted the maximum number of times, a clear
            should still succeed.
            """
            videos = []
            for v in Video.objects.all()[:3]:
                v.categories.add(self.category)
                videos.append(v)

            c = Client()
            c.login(username='user', password='password')

            for video in videos:
                c.post(reverse('localtv_video_vote',
                               args=(video.pk,
                                     'up')))

            self.assertEqual(
                Vote.objects.count(),
                3)

            c.post(reverse('localtv_video_vote',
                           args=(video.pk,
                                 'clear')))
            self.assertEqual(
                Vote.objects.count(),
                2)

        def test_voting_view_requires_authentication(self):
            """
            The user must be logged in in order to vote.
            """
            self.assertRequiresAuthentication(reverse('localtv_video_vote',
                                                      args=(self.video.pk,
                                                            'up')))

        def test_voting_view_voting_disabled(self):
            """
            If voting is not enabled for a category on the video, voting should
            have no effect.
            """
            self.video.categories.clear()
            c = Client()
            c.login(username='user', password='password')
            response = c.post(reverse('localtv_video_vote',
                                      args=(self.video.pk,
                                            'up')))
            self.assertStatusCodeEquals(response, 302)
            self.assertEqual(response['Location'],
                             'http://testserver%s' % (
                    self.video.get_absolute_url()))
            self.assertEqual(
                Vote.objects.count(),
                0)

        def test_video_model_voting_enabled(self):
            """
            Video.voting_enabled() should be True if it has a voting-enabled
            category, else False.
            """
            self.assertTrue(self.video.voting_enabled())
            self.assertFalse(Video.objects.get(pk=1).voting_enabled())

        def test_video_view_user_can_vote_True(self):
            """
            The view_video view should have a 'user_can_vote' variable which is
            True if the user has not used all their votes.
            """
            c = Client()
            c.login(username='user', password='password')

            response = c.get(self.video.get_absolute_url())
            self.assertTrue(response.context['user_can_vote'])

        def test_video_view_user_can_vote_False(self):
            """
            If the user has used all of their votes, 'user_can_vote' should be
            False.
            """
            c = Client()
            c.login(username='user', password='password')

            for video in Video.objects.all()[:3]:
                video.categories.add(self.category)
                c.post(reverse('localtv_video_vote',
                               args=(video.pk,
                                     'up')))

            response = c.get(self.video.get_absolute_url())
            self.assertFalse(response.context['user_can_vote'])

