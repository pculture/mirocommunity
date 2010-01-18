# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
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
import os.path
from urllib import quote_plus

import feedparser
import vidscraper

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments import get_model, get_form, get_form_target
Comment = get_model()
CommentForm = get_form()

from django.core import mail
from django.core.urlresolvers import get_resolver, reverse
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.test import TestCase
from django.test.client import Client

from localtv import models
from localtv import util

class BaseTestCase(TestCase):
    fixtures = ['site', 'users']

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
        self.site_location = models.SiteLocation.objects.get(
            site=settings.SITE_ID)

    def tearDown(self):
        TestCase.tearDown(self)
        settings.SITE_ID = self.old_site_id
        for profile in util.get_profile_model().objects.all():
            if profile.logo:
                profile.logo.delete()
        for category in models.Category.objects.all():
            if category.logo:
                category.logo.delete()
        if self.site_location.logo:
            self.site_location.logo.delete()
        if self.site_location.background:
            self.site_location.background.delete()

    def _data_file(self, filename):
        """
        Returns the absolute path to a file in our testdata directory.
        """
        return os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                'testdata',
                filename))

    def assertIsInstance(self, obj, klass):
        """
        Assert that the given object is an instance of the given class.

        @param obj: the object we are testing
        @param klass: the klass the object should be an instance of
        """
        self.assertTrue(isinstance(obj, klass),
                        "%r is not an instance of %r; %s instead" % (
                obj, klass, type(obj)))

    def assertStatusCodeEquals(self, response, status_code):
        """
        Assert that the response has the given status code.  If not, give a
        useful error mesage.
        """
        self.assertEquals(response.status_code, status_code,
                          'Status Code: %i != %i\nData: %s' % (
                response.status_code, status_code,
                response.content))

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
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s?next=%s' %
                          (self.site_location.site.domain,
                           settings.LOGIN_URL,
                           quote_plus(url)))


# -----------------------------------------------------------------------------
# Feed tests
# -----------------------------------------------------------------------------

class MockVidScraper(object):

    errors = vidscraper.errors

    def auto_scrape(self, link, fields=None):
        raise vidscraper.errors.Error('could not scrape %s' % link)

class FeedModelTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['feeds']

    def setUp(self):
        BaseTestCase.setUp(self)
        self.vidscraper = models.vidscraper
        models.vidscraper = MockVidScraper()

    def tearDown(self):
        BaseTestCase.tearDown(self)
        models.vidscraper = self.vidscraper
        del self.vidscraper

    def test_auto_approve_True(self):
        """
        If Feed.auto_approve is True, the imported videos should be marked as
        active.
        """
        feed = models.Feed.objects.get(pk=1)
        feed.auto_approve = True
        feed.feed_url = self._data_file('feed.rss')
        feed.update_items()
        self.assertEquals(models.Video.objects.count(), 5)
        self.assertEquals(models.Video.objects.filter(
                status=models.VIDEO_STATUS_ACTIVE).count(), 5)

    def test_auto_approve_False(self):
        """
        If Feed.auto_approve is False, the imported videos should be marked as
        unapproved.
        """
        feed = models.Feed.objects.get(pk=1)
        feed.auto_approve = False
        feed.feed_url = self._data_file('feed.rss')
        feed.update_items()
        self.assertEquals(models.Video.objects.count(), 5)
        self.assertEquals(models.Video.objects.filter(
                status=models.VIDEO_STATUS_UNAPPROVED).count(), 5)

    def test_uses_given_parsed_feed(self):
        """
        When adding entries in update_items with a given FeedParser instance,
        the method should not download the feed itself.
        """
        parsed_feed = feedparser.parse(self._data_file('feed.rss'))
        feed = models.Feed.objects.get(pk=1)
        feed.update_items(parsed_feed=parsed_feed)
        parsed_guids = reversed([entry.guid for entry in parsed_feed.entries])
        db_guids = models.Video.objects.order_by('id').values_list('guid',
                                                                   flat=True)
        self.assertEquals(list(parsed_guids), list(db_guids))

    def test_entries_inserted_in_reverse_order(self):
        """
        When adding entries from a feed, they should be added to the database
        in rever order (oldest first)
        """
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed.rss')
        feed.update_items()
        parsed_feed = feedparser.parse(feed.feed_url)
        parsed_guids = reversed([entry.guid for entry in parsed_feed.entries])
        db_guids = models.Video.objects.order_by('id').values_list('guid',
                                                                   flat=True)
        self.assertEquals(list(parsed_guids), list(db_guids))

    def test_ignore_duplicate_guid(self):
        """
        If the GUID already exists for this feed, the newer item should be
        skipped.
        """
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed_with_duplicate_guid.rss')
        feed.update_items()
        self.assertEquals(models.Video.objects.count(), 1)
        self.assertEquals(models.Video.objects.get().name, 'Old Item')

    def test_ignore_duplicate_link(self):
        """
        If the GUID already exists for this feed, the newer item should be
        skipped.
        """
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed_with_duplicate_link.rss')
        feed.update_items()
        self.assertEquals(models.Video.objects.count(), 1)
        self.assertEquals(models.Video.objects.get().name, 'Old Item')

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
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed.rss')
        feed.update_items()
        video = models.Video.objects.order_by('id')[0]
        self.assertEquals(video.feed, feed)
        self.assertEquals(video.guid, u'23C59362-FC55-11DC-AF3F-9C4011C4A055')
        self.assertEquals(video.name, u'Dave Glassco Supports Miro')
        self.assertEquals(video.description,
                          '>\n\n<br />\n\nDave is a great advocate and '
                          'supporter of Miro.')
        self.assertEquals(video.website_url, 'http://blip.tv/file/779122')
        self.assertEquals(video.file_url,
                          'http://blip.tv/file/get/'
                          'Miropcf-DaveGlasscoSupportsMiro942.mp4')
        self.assertEquals(video.file_url_length, 16018279)
        self.assertEquals(video.file_url_mimetype, 'video/mp4')
        self.assertTrue(video.has_thumbnail)
        self.assertEquals(video.thumbnail_url,
                          'http://e.static.blip.tv/'
                          'Miropcf-DaveGlasscoSupportsMiro959.jpg')
        self.assertEquals(video.when_published,
                          datetime.datetime(2008, 3, 27, 23, 25, 51))
        self.assertEquals(video.video_service(), 'blip.tv')
        category = ['Default Category']
        if getattr(settings, 'FORCE_LOWERCASE_TAGS', False):
            category = [category[0].lower()]
        self.assertEquals([tag.name for tag in video.tags.all()],
                          category)

    def test_entries_link_optional(self):
        """
        A link in the feed to the original source should be optional.
        """
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed_without_link.rss')
        feed.update_items()
        video = models.Video.objects.order_by('id')[0]
        self.assertEquals(video.feed, feed)
        self.assertEquals(video.guid, u'D9E50330-F6E1-11DD-A117-BB8AB007511B')

    def test_entries_enclosure_type_optional(self):
        """
        An enclosure without a MIME type, but with a file URL extension we
        think is media, should be imported.
        """
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed_without_mime_type.rss')
        feed.update_items()
        video = models.Video.objects.order_by('id')[0]
        self.assertEquals(video.feed, feed)
        self.assertEquals(video.guid, u'D9E50330-F6E1-11DD-A117-BB8AB007511B')

    def test_entries_vimeo(self):
        """
        Vimeo RSS feeds should include the correct data.
        """
        models.vidscraper = self.vidscraper
        feed = models.Feed.objects.get(pk=1)
        feed.auto_authors = [User.objects.get(pk=1)]
        feed.feed_url = self._data_file('vimeo.rss')
        feed.update_items()
        video = models.Video.objects.order_by('id')[0]
        self.assertEquals(video.feed, feed)
        self.assertEquals(video.guid, u'tag:vimeo,2009-12-04:clip7981161')
        self.assertEquals(video.name, u'Tishana - Pro-Choicers on Stupak')
        self.assertEquals(video.description,
                          '<p><a href="http://vimeo.com/7981161"></a></p><p>'
                          'Tishana from SPARK Reproductive Justice talking '
                          'about the right to choose after the National Day '
                          'of Action Rally to Stop Stupak-Pitts, 12.2.2009\n'
                          '</p><p>Cast: <a href="http://vimeo.com/user1751935"'
                          ' style="color: #2786c2; text-decoration: none;">'
                          'Latoya Peterson</a></p>')
        self.assertEquals(video.website_url, 'http://vimeo.com/7981161')
        self.assertEquals(video.embed_code,
                          '<object width="425" height="344">'
                          '<param name="allowfullscreen" value="true">'
                          '<param name="allowscriptaccess" value="always">'
                          '<param name="movie" value="http://vimeo.com/'
                          'moogaloop.swf?show_byline=1&amp;fullscreen=1&amp;'
                          'clip_id=7981161&amp;color=&amp;'
                          'server=vimeo.com&amp;show_title=1&amp;'
                          'show_portrait=0"><embed src="http://vimeo.com/'
                          'moogaloop.swf?show_byline=1&amp;fullscreen=1&amp;'
                          'clip_id=7981161&amp;color=&amp;'
                          'server=vimeo.com&amp;show_title=1&amp;'
                          'show_portrait=0" allowscriptaccess="always" '
                          'height="344" width="425" allowfullscreen="true" '
                          'type="application/x-shockwave-flash"></embed>'
                          '</object>')
        self.assertEquals(video.file_url, '')
        self.assertTrue(video.has_thumbnail)
        self.assertEquals(video.thumbnail_url,
                          'http://ts.vimeo.com.s3.amazonaws.com/360/198/'
                          '36019806_640.jpg')
        self.assertEquals(video.when_published,
                          datetime.datetime(2009, 12, 4, 8, 23, 47))
        self.assertEquals(video.video_service(), 'Vimeo')
        category = ['Pro-Choice', 'Stupak-Pitts']
        if getattr(settings, 'FORCE_LOWERCASE_TAGS', False):
            category = [cat.lower() for cat in category]
        self.assertEquals([tag.name for tag in video.tags.all()],
                          category)
        self.assertEquals(list(video.authors.values_list('username')),
                          [('Latoya Peterson',)])

    def test_entries_atom(self):
        """
        Atom feeds should be handled correctly,
        """
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed.atom')
        feed.update_items()
        video = models.Video.objects.order_by('id')[0]
        self.assertEquals(video.feed, feed)
        self.assertEquals(video.guid, u'http://www.example.org/entries/1')
        self.assertEquals(video.name, u'Atom 1.0')
        self.assertEquals(video.when_published, datetime.datetime(2005, 7, 15,
                                                                  12, 0, 0))
        self.assertEquals(video.file_url,
                          u'http://www.example.org/myvideo.ogg')
        self.assertEquals(video.file_url_length, 1234)
        self.assertEquals(video.file_url_mimetype, u'application/ogg')
        self.assertEquals(video.website_url,
                          u'http://www.example.org/entries/1')
        self.assertEquals(video.description, u"""<h1>Show Notes</h1>
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
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed_from_mc.atom')
        feed.update_items()
        video = models.Video.objects.order_by('id')[0]
        self.assertEquals(video.feed, feed)
        self.assertEquals(video.guid,
                          u'http://www.onnetworks.com/5843 at '
                          'http://www.onnetworks.com')
        self.assertEquals(video.name, u'"The Dancer & Kenaudra"')
        self.assertEquals(video.when_published,
                          datetime.datetime(2009, 1, 13, 6, 0))
        self.assertEquals(video.file_url,
                          u'http://podcast.onnetworks.com/videos/'
                          'sgatp_0108_kenaudra_480x270.mp4?feed=video'
                          '&key=6100&target=itunes')
        self.assertEquals(video.file_url_length, 1)
        self.assertEquals(video.file_url_mimetype, u'video/mp4')
        self.assertEquals(video.website_url,
                          u'http://www.onnetworks.com/videos/'
                          'smart-girls-at-the-party/the-dancer-kenaudra')
        self.assertEquals(video.description,
                          u'Kenaudra displays her many talents including a '
                          'new dance called Praise Dancing.<br />'
                          '<a href="http://www.onnetworks.com/videos/'
                          'smart-girls-at-the-party/the-dancer-kenaudra"></a>')
        self.assertEquals(video.embed_code,
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
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed_with_link_via.atom')
        feed.update_items()
        video = models.Video.objects.order_by('id')[0]
        self.assertEquals(video.feed, feed)
        self.assertEquals(video.website_url,
                          u'http://www.example.org/entries/1')

    def test_entries_atom_with_media(self):
        """
        Atom feeds that use Yahoo!'s Media RSS specification should also have
        their content imported,
        """
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed_with_media.atom')
        feed.update_items()
        video = models.Video.objects.order_by('id')[0]
        self.assertEquals(video.feed, feed)
        self.assertEquals(video.file_url,
                          u'http://www.example.org/myvideo.ogg')
        self.assertEquals(video.file_url_mimetype, u'application/ogg')
        self.assertEquals(video.thumbnail_url,
                          'http://www.example.org/myvideo.jpg')

    def test_entries_atom_with_media_player(self):
        """
        Atom feeds that use Yahoo!'s Media RSS specification to include an
        embeddable player (with <media:player> should have that code included,
        """
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed_with_media_player.atom')
        feed.update_items()
        video = models.Video.objects.order_by('id')[0]
        self.assertEquals(video.feed, feed)
        self.assertEquals(video.embed_code,
                          '<embed src="http://www.example.org/?a=b&c=d">')

    def test_entries_atom_with_invalid_media(self):
        """
        Atom feeds that incorrectly use Yahoo!'s Media RSS specification (and
        don't specify a video another way) should be ignored.
        """
        feed = models.Feed.objects.get(pk=1)
        feed.feed_url = self._data_file('feed_with_invalid_media.atom')
        feed.update_items()
        self.assertEquals(feed.video_set.count(), 0)

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

        feed = models.Feed.objects.get(pk=1)
        for service, url in services:
            feed.feed_url = url
            self.assertEquals(feed.video_service(), service,
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
        for watched in models.Watch.objects.all():
            watched.timestamp = datetime.datetime.now() # so that they're
                                                        # recent
            watched.save()

        c = Client()
        response = c.get(reverse('localtv_index'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/index.html')
        self.assertEquals(list(response.context['featured_videos']),
                          list(models.Video.objects.filter(
                    status=models.VIDEO_STATUS_ACTIVE,
                    last_featured__isnull=False)))
        self.assertEquals(list(response.context['popular_videos']),
                          list(models.Video.objects.popular_since(
                    datetime.timedelta.max,
                    status=models.VIDEO_STATUS_ACTIVE)))
        self.assertEquals(list(response.context['new_videos']),
                          list(models.Video.objects.new(
                    status=models.VIDEO_STATUS_ACTIVE)))

    def test_about(self):
        """
        The about view should render the 'localtv/about.html' template.
        """
        c = Client()
        response = c.get(reverse('localtv_about'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/about.html')

    def test_view_video(self):
        """
        The view_video view should render the 'localtv/view_video.html'
        template.  It should include the current video, and a QuerySet of other
        popular videos.
        """
        for watched in models.Watch.objects.all():
            watched.timestamp = datetime.datetime.now() # so that they're
                                                        # recent
            watched.save()

        video = models.Video.objects.get(pk=20)

        c = Client()
        response = c.get(video.get_absolute_url())
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/view_video.html')
        self.assertEquals(response.context[0]['current_video'], video)
        self.assertEquals(list(response.context[0]['popular_videos']),
                          list(models.Video.objects.popular_since(
                    datetime.timedelta.max,
                    status=models.VIDEO_STATUS_ACTIVE)))

    def test_view_video_admins_see_rejected(self):
        """
        The view_video view should return a 404 for rejected videos, unless the
        user is an admin.
        """
        video = models.Video.objects.get(pk=1)

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
        video = models.Video.objects.get(pk=20)

        c = Client()
        response = c.get(reverse('localtv_view_video',
                                 args=[20, 'wrong-slug']))
        # 301 is a permanent redirect
        self.assertStatusCodeEquals(response, 301)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                video.get_absolute_url()))

        response = c.get(reverse('localtv_view_video',
                                 args=[20, '']))
        self.assertStatusCodeEquals(response, 301)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                video.get_absolute_url()))

    def test_view_video_category(self):
        """
        If the video has categories, the view_video view should include a
        category in the template and those videos should be shown in place of
        the regular popular videos.
        """
        video = models.Video.objects.get(pk=20)
        video.categories = [2]
        video.save()

        c = Client()
        response = c.get(video.get_absolute_url(),
                         HTTP_HOST=self.site_location.site.domain,
                         HTTP_REFERER='http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_category',
                        args=['miro'])))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.context['category'].pk, 1)
        self.assertEquals(list(response.context[0]['popular_videos']),
                          list(models.Video.objects.popular_since(
                    datetime.timedelta.max,
                    categories__pk=1,
                    status=models.VIDEO_STATUS_ACTIVE)))

    def test_view_video_category_referer(self):
        """
        If the view_video referrer was a category page, that category should be
        included in the template and those videos should be shown in place of
        the regular popular videos.
        """
        video = models.Video.objects.get(pk=20)
        video.categories = [1, 2]
        video.save()

        c = Client()
        response = c.get(video.get_absolute_url(),
                         HTTP_HOST=self.site_location.site.domain,
                         HTTP_REFERER='http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_category',
                        args=['miro'])))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.context['category'].pk, 1)
        self.assertEquals(list(response.context[0]['popular_videos']),
                          list(models.Video.objects.popular_since(
                    datetime.timedelta.max,
                    categories__pk=1,
                    status=models.VIDEO_STATUS_ACTIVE)))

    def test_video_search(self):
        """
        The video_search view should take a GET['query'] and search through the
        videos.  It should render the
        'localtv/video_listing_search.html' template.
        """
        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'query': 'blend'}) # lots of Blender videos in the
                                             # test data
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/video_listing_search.html')
        self.assertEquals(response.context['page'], 1)
        self.assertEquals(response.context['pages'], 4)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          list(models.Video.objects.filter(
                    Q(name__icontains="blend") |
                    Q(description__icontains="blend") |
                    Q(feed__name__icontains="blend"),
                    status=models.VIDEO_STATUS_ACTIVE)[:5]))

    def test_video_search_no_query(self):
        """
        The video_search view should render the
        'localtv/video_listing_search.html' template.
        """
        c = Client()
        response = c.get(reverse('localtv_search'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/video_listing_search.html')

    def test_video_search_pagination(self):
        """
        The video_search view should take a GET['page'] argument which shows
        the next page of search results.
        """
        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'query': 'blend',
                          'page': 2})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.context['page'], 2)
        self.assertEquals(response.context['pages'], 4)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          list(models.Video.objects.filter(
                    Q(name__icontains="blend") |
                    Q(description__icontains="blend") |
                    Q(feed__name__icontains="blend"),
                    status=models.VIDEO_STATUS_ACTIVE)[5:10]))

    def test_video_search_includes_tags(self):
        """
        The video_search view should search the tags for videos.
        """
        video = models.Video.objects.get(pk=20)
        video.tags = 'tag1 tag2'
        video.save()

        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'query': 'tag1'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.context['page'], 1)
        self.assertEquals(response.context['pages'], 1)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'query': 'tag2'})
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'query': 'tag2 tag1'})
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

    def test_video_search_includes_categories(self):
        """
        The video_search view should search the category for videos.
        """
        video = models.Video.objects.get(pk=20)
        video.categories = [1, 2] # Miro, Linux
        video.save()

        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'query': 'Miro'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.context['page'], 1)
        self.assertEquals(response.context['pages'], 1)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'query': 'Linux'})
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'query': 'Miro Linux'})
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

    def test_video_search_includes_user(self):
        """
        The video_search view should search the user who submitted videos.
        """
        video = models.Video.objects.get(pk=20)
        video.user = User.objects.get(username='user')
        video.save()

        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'query': 'user'}) # username
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.context['page'], 1)
        self.assertEquals(response.context['pages'], 1)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'query': 'firstname'}) # first name
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

        response = c.get(reverse('localtv_search'),
                         {'query': 'lastname'}) # last name
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

    def test_video_search_includes_video_service_user(self):
        """
        The video_search view should search the video service user for videos.
        """
        video = models.Video.objects.get(pk=20)
        video.video_service_user = 'Video_service_user'
        video.save()

        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'query': 'video_service_user'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.context['page'], 1)
        self.assertEquals(response.context['pages'], 1)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

    def test_video_search_includes_feed_name(self):
        """
        The video_search view should search the feed name for videos.
        """
        video = models.Video.objects.get(pk=20)
        # feed is miropcf

        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'query': 'miropcf'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.context['page'], 1)
        self.assertEquals(response.context['pages'], 1)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

    def test_video_search_exclude_terms(self):
        """
        The video_search view should exclude terms that start with - (hyphen).
        """
        c = Client()
        response = c.get(reverse('localtv_search'),
                         {'query': '-blender'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.context['pages'], 2)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          list(models.Video.objects.filter(
                    status=models.VIDEO_STATUS_ACTIVE).exclude(
                    name__icontains='blender').exclude(
                    description__icontains='blender').exclude(
                    feed__name__icontains='blender')[:5]))

    def test_category_index(self):
        """
        The category_index view should render the
        'localtv/categories.html' template and include the root
        categories (those without parents).
        """
        c = Client()
        response = c.get(reverse('localtv_category_index'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/categories.html')
        self.assertEquals(response.context['pages'], 1)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          list(models.Category.objects.filter(parent=None)))

    def test_category(self):
        """
        The category view should render the 'localtv/category.html'
        template, and include the appropriate category.
        """
        category = models.Category.objects.get(slug='miro')
        c = Client()
        response = c.get(category.get_absolute_url())
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/category.html')
        self.assertEquals(response.context['category'], category)

    def test_author_index(self):
        """
        The author_index view should render the
        'localtv/author_list.html' template and include the authors in
        the context.
        """
        c = Client()
        response = c.get(reverse('localtv_author_index'))
        self.assertEquals(response.template[0].name,
                          'localtv/author_list.html')
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(list(response.context['authors']),
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
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/author.html')
        self.assertEquals(response.context['author'], author)
        self.assertEquals(len(response.context['video_list']), 2)
        self.assertEquals(list(response.context['video_list']),
                          list(models.Video.objects.filter(
                    Q(user=author) | Q(authors=author),
                    status=models.VIDEO_STATUS_ACTIVE)))


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
        self.assertEquals(response.template[0].name,
                          'localtv/browse.html')

    def test_new_videos(self):
        """
        The new_videos view should render the
        'localtv/video_listing_new.html' template and include the new
        videos.
        """
        c = Client()
        response = c.get(reverse('localtv_list_new'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/video_listing_new.html')
        self.assertEquals(response.context['pages'], 2)
        self.assertEquals(len(response.context['page_obj'].object_list), 15)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          list(models.Video.objects.new(
                    status=models.VIDEO_STATUS_ACTIVE)[:15]))

    def test_popular_videos(self):
        """
        The popular_videos view should render the
        'localtv/video_listing_popular.html' template and include the
        popular videos.
        """
        for w in models.Watch.objects.all():
            w.timestamp = datetime.datetime.now()
            w.save()

        c = Client()
        response = c.get(reverse('localtv_list_popular'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/video_listing_popular.html')
        self.assertEquals(response.context['pages'], 1)
        self.assertEquals(len(response.context['page_obj'].object_list), 2)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          list(models.Video.objects.popular_since(
                    datetime.timedelta.max,
                    watch__timestamp__gte=datetime.datetime.min,
                    status=models.VIDEO_STATUS_ACTIVE)))

    def test_featured_videos(self):
        """
        The featured_videos view should render the
        'localtv/video_listing_featured.html' template and include the
        featured videos.
        """
        c = Client()
        response = c.get(reverse('localtv_list_featured'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/video_listing_featured.html')
        self.assertEquals(response.context['pages'], 1)
        self.assertEquals(len(response.context['page_obj'].object_list), 2)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          list(models.Video.objects.filter(
                    last_featured__isnull=False,
                    status=models.VIDEO_STATUS_ACTIVE)))

    def test_tag_videos(self):
        """
        The tag_videos view should render the
        'localtv/video_listing_tag.html' template and include the
        tagged videos.
        """
        video = models.Video.objects.get(pk=20)
        video.tags = 'tag1'
        video.save()

        c = Client()
        response = c.get(reverse('localtv_list_tag',
                         args=['tag1']))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/video_listing_tag.html')
        self.assertEquals(response.context['pages'], 1)
        self.assertEquals(len(response.context['page_obj'].object_list), 1)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          [video])

    def test_feed_videos(self):
        """
        The feed_videos view should render the
        'localtv/video_listing_feed.html' template and include the
        videos from the given feed.
        """
        feed = models.Feed.objects.get(pk=1)

        c = Client()
        response = c.get(reverse('localtv_list_feed',
                                 args=[feed.pk]))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/video_listing_feed.html')
        self.assertEquals(response.context['pages'], 1)
        self.assertEquals(len(response.context['page_obj'].object_list), 1)
        self.assertEquals(list(response.context['page_obj'].object_list),
                          list(feed.video_set.filter(
                    status=models.VIDEO_STATUS_ACTIVE)))


# -----------------------------------------------------------------------------
# Comment moderation tests
# -----------------------------------------------------------------------------

class CommentModerationTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['videos']

    def setUp(self):
        BaseTestCase.setUp(self)
        self.video = models.Video.objects.get(pk=20)
        self.url = get_form_target()
        self.form = CommentForm(self.video,
                                initial={
                'name': 'postname',
                'email': 'post@email.com',
                'url': 'http://posturl.com/'})
        self.POST_data = self.form.initial
        self.POST_data['comment'] = 'comment string'

    def test_comment_does_not_require_email_or_url(self):
        """
        Posting a comment should not require an e-mail address or URL.
        """
        del self.POST_data['email']
        del self.POST_data['url']

        c = Client()
        c.post(self.url, self.POST_data)
        comment = Comment.objects.get()
        self.assertEquals(comment.content_object, self.video)
        self.assertFalse(comment.is_public)
        self.assertEquals(comment.name, 'postname')
        self.assertEquals(comment.email, '')
        self.assertEquals(comment.url, '')

    def test_screen_all_comments_False(self):
        """
        If SiteLocation.screen_all_comments is False, the comment should be
        saved and marked as public.
        """
        self.site_location.screen_all_comments = False
        self.site_location.save()

        c = Client()
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEquals(comment.content_object, self.video)
        self.assertTrue(comment.is_public)
        self.assertEquals(comment.name, 'postname')
        self.assertEquals(comment.email, 'post@email.com')
        self.assertEquals(comment.url, 'http://posturl.com/')

    def test_screen_all_comments_True(self):
        """
        If SiteLocation.screen_all_comments is True, the comment should be
        moderated (not public).
        """
        c = Client()
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEquals(comment.content_object, self.video)
        self.assertFalse(comment.is_public)
        self.assertEquals(comment.name, 'postname')
        self.assertEquals(comment.email, 'post@email.com')
        self.assertEquals(comment.url, 'http://posturl.com/')

    def test_screen_all_comments_True_admin(self):
        """
        Even if SiteLocation,screen_all_comments is True, comments from logged
        in admins should not be screened.
        """
        self.site_location.screen_all_comments = True
        self.site_location.save()

        c = Client()
        c.login(username='admin', password='admin')
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEquals(comment.content_object, self.video)
        self.assertTrue(comment.is_public)
        comment.delete()

        c.login(username='superuser', password='superuser')
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEquals(comment.content_object, self.video)
        self.assertTrue(comment.is_public)

    def test_comments_email_admins_False(self):
        """
        If SiteLocation.comments_email_admins is False, no e-mail should be
        sent when a comment is made.
        """
        c = Client()
        c.post(self.url, self.POST_data)

        self.assertEquals(mail.outbox, [])

    def test_comments_email_admins_True(self):
        """
        If SiteLocation.comments_email_admins is True, an e-mail should be
        sent when a comment is made to each admin/superuser.
        """
        self.site_location.comments_email_admins = True
        self.site_location.save()

        c = Client()
        c.post(self.url, self.POST_data)

        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].recipients(),
                          ['admin@testserver.local',
                           'superuser@testserver.local'])

    def test_comments_required_login_False(self):
        """
        If SiteLocation.comments_required_login is False, comments should be
        allowed by any user.  This is the same test code as
        test_screen_all_comments_False().
        """
        c = Client()
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEquals(comment.content_object, self.video)
        self.assertFalse(comment.is_public)
        self.assertEquals(comment.name, 'postname')
        self.assertEquals(comment.email, 'post@email.com')
        self.assertEquals(comment.url, 'http://posturl.com/')

    def test_comments_required_login_True(self):
        """
        If SiteLocation.comments_required_login, making a comment should
        require a logged-in user.
        """
        self.site_location.comments_required_login = True
        self.site_location.save()

        c = Client()
        response = c.post(self.url, self.POST_data)
        self.assertStatusCodeEquals(response, 400)
        self.assertEquals(Comment.objects.count(), 0)

        c.login(username='user', password='password')
        c.post(self.url, self.POST_data)

        comment = Comment.objects.get()
        self.assertEquals(comment.content_object, self.video)
        self.assertFalse(comment.is_public)
        self.assertEquals(comment.name, 'Firstname Lastname')
        self.assertEquals(comment.email, 'user@testserver.local')
        self.assertEquals(comment.url, 'http://posturl.com/')

# -----------------------------------------------------------------------------
# HttpMixedReplaceResponse tests
# -----------------------------------------------------------------------------

class HttpMixedReplaceResponseTestCase(BaseTestCase):

    def _request(self, user_agent='Mozilla/5.0'):
        """
        Returns an HttpRequest() object with the given user agent.
        """
        request = HttpRequest()
        request.META['HTTP_USER_AGENT'] = user_agent
        return request

    def test_basic(self):
        """
        HttpMixedReplaceResponse takes a request and a generator, and returns
        each response as a part of an multiplart/mixed-replace response.
        """
        response1 = HttpResponse('response1', content_type='text/plain')
        response2 = HttpResponse('response2')
        def gen():
            yield response1
            yield response2

        mixed_response = util.HttpMixedReplaceResponse(
            self._request(), gen())

        self.assertEquals(mixed_response['Content-Type'].split(';')[0],
                          'multipart/x-mixed-replace')

        boundary = mixed_response['Content-Type'].split('"')[1]
        self.assertEquals(mixed_response.content, """--%(boundary)s\
Content-Type: text/plain

%(response1)s
--%(boundary)s\
Content-Type: text/html; charset=utf-8

%(response2)s
--%(boundary)s--""" % {
                'boundary': boundary,
                'response1': response1.content,
                'response2': response2.content
                })

    def test_safari(self):
        """
        If the user-agent is Safari, just return the last response.  Safari
        sometimes freaks out when handling this type of response.
        """
        response1 = HttpResponse('response1', content_type='text/plain')
        response2 = HttpResponse('response2')
        def gen():
            yield response1
            yield response2

        mixed_response = util.HttpMixedReplaceResponse(
            self._request('Safari'), gen())

        self.assertEquals(mixed_response['Content-Type'],
                          response2['Content-Type'])
        self.assertEquals(mixed_response.content,
                          response2.content)

    def test_error(self):
        """
        If one of the responses raises an exception, a 500 page should be
        rendered.
        """
        response1 = HttpResponse('response1', content_type='text/plain')
        def gen():
            yield response1
            raise IndexError('should get caught')

        request = self._request()
        mixed_response = util.HttpMixedReplaceResponse(
            request, gen())

        self.assertEquals(mixed_response['Content-Type'].split(';')[0],
                          'multipart/x-mixed-replace')

        error_view = get_resolver(None).resolve500()
        error_response = error_view[0](request, **error_view[1])
        boundary = mixed_response['Content-Type'].split('"')[1]
        self.assertEquals(mixed_response.content, """--%(boundary)s\
Content-Type: text/plain

%(response1)s
--%(boundary)s\
Content-Type: text/html; charset=utf-8

%(error_response)s
--%(boundary)s--""" % {
                'boundary': boundary,
                'response1': response1.content,
                'error_response': error_response.content
                })

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
        v = models.Video.objects.get(pk=11)
        self.assertEquals(v.when(), v.when_published)
        v.when_published = None
        self.assertEquals(v.when(), v.when_approved)
        v.when_approved = None
        self.assertEquals(v.when(), v.when_submitted)

    def test_when_use_original_date_False(self):
        """
        When SiteLocation.use_original_date is False, Video.when() ignores the
        when_published date.
        """
        self.site_location.use_original_date = False
        self.site_location.save()
        v = models.Video.objects.get(pk=11)
        self.assertEquals(v.when(), v.when_approved)


    def test_when_prefix(self):
        """
        Video.when_prefix() returns 'published' if the date is
        when_published, otherwise it returns 'posted'..
        """
        v = models.Video.objects.get(pk=11)
        self.assertEquals(v.when_prefix(), 'published')
        v.when_published = None
        self.assertEquals(v.when_prefix(), 'posted')

    def test_when_prefix_use_original_date_False(self):
        """
        When SiteLocation.use_original_date is False, Video.when_prefix()
        returns 'posted'.
        """
        self.site_location.use_original_date = False
        self.site_location.save()
        v = models.Video.objects.get(pk=11)
        self.assertEquals(v.when_prefix(), 'posted')

    def test_new(self):
        """
        Video.objects.new() should return a QuerySet ordered by the best
        available date:

        1) when_published
        2) when_approved
        3) when_submitted
        """
        self.assertEquals(list(models.Video.objects.new()),
                          list(models.Video.objects.extra(select={'date': """
COALESCE(localtv_video.when_published,localtv_video.when_approved,
localtv_video.when_submitted)"""}).order_by('-date')))

    def test_new_use_original_date_False(self):
        """
        When SiteLocation.use_original_date is False, Video.objects.new()
        should ignore the when_published date.
        """
        self.site_location.use_original_date = False
        self.site_location.save()
        self.assertEquals(list(models.Video.objects.new(
                    site=self.site_location.site)),
                          list(models.Video.objects.extra(select={'date': """
COALESCE(localtv_video.when_approved,localtv_video.when_submitted)"""}
                                                          ).order_by('-date')))

        
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

        video = models.Video.objects.get(pk=1)

        models.Watch.add(request, video)

        watch = models.Watch.objects.get()
        self.assertEquals(watch.video, video)
        self.assertTrue(watch.timestamp - datetime.datetime.now() <
                        datetime.timedelta(seconds=1))
        self.assertEquals(watch.user, request.user)
        self.assertEquals(watch.ip_address, request.META['REMOTE_ADDR'])

    def test_add_unauthenticated(self):
        """
        Unauthenticated requests should add a Watch object with user set to
        None.
        """
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = '123.123.123.123'

        video = models.Video.objects.get(pk=1)

        models.Watch.add(request, video)

        watch = models.Watch.objects.get()
        self.assertEquals(watch.video, video)
        self.assertTrue(watch.timestamp - datetime.datetime.now() <
                        datetime.timedelta(seconds=1))
        self.assertEquals(watch.user, None)
        self.assertEquals(watch.ip_address, request.META['REMOTE_ADDR'])

    def test_add_invalid_ip(self):
        """
        Requests with an invalid IP address should not raise an error.  The IP
        address should be saved as 0.0.0.0.
        """
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = 'unknown'

        video = models.Video.objects.get(pk=1)

        models.Watch.add(request, video)

        w = models.Watch.objects.get()
        self.assertEquals(w.video, video)
        self.assertEquals(w.ip_address, '0.0.0.0')


# -----------------------------------------------------------------------------
# SavedSearch model tests
# -----------------------------------------------------------------------------

class SavedSearchModelTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['savedsearches']

    def test_update_items(self):
        """
        SavedSearch.update_items() should create new Video objects linked to
        the search.
        """
        ss = models.SavedSearch.objects.get(pk=1)
        self.assertEquals(ss.video_set.count(), 0)
        ss.update_items()
        self.assertEquals(ss.video_set.count(), 1)

    def test_update_items_ignore_duplicates(self):
        """
        A search that includes the same video should should not add the video a
        second time.
        """
        ss = models.SavedSearch.objects.get(pk=1)
        ss.update_items()
        self.assertEquals(ss.video_set.count(), 1)
        ss.update_items()
        self.assertEquals(ss.video_set.count(), 1)
