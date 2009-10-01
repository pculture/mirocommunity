import datetime
import os.path
from urllib import quote_plus, urlencode

import feedparser
import vidscraper

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from localtv import models


class BaseTestCase(TestCase):
    fixtures = ['site', 'users']

    def setUp(self):
        TestCase.setUp(self)
        self.old_site_id = settings.SITE_ID
        settings.SITE_ID = 1
        self.site_location = models.SiteLocation.objects.get(
            site=settings.SITE_ID)

    def tearDown(self):
        TestCase.tearDown(self)
        settings.SITE_ID = self.old_site_id

    def assertRequiresAuthentication(self, url, *args,
                                     **kwargs):
        """
        Assert that the given URL requires the user to be authenticated.

        If additional arguments are passed, they are passed to the Client.get
        method

        If keyword arguments are present, they're passed to Client.login before
        the URL is accessed.

        @param url_or_reverse: the URL to access, or a name we can reverse
        """
        c = Client()

        if kwargs:
            c.login(**kwargs)

        response = c.get(url, *args)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s?next=%s' %
                          (self.site_location.site.domain,
                           settings.LOGIN_URL,
                           quote_plus(url)))

# -----------------------------------------------------------------------------
# Video submit tests
# -----------------------------------------------------------------------------

class SubmitVideoBaseTestCase(BaseTestCase):
    abstract = True
    url = None
    GET_data = {}

    def run(self, *args, **kwargs):
        # hack to prevent the test runner from treating abstract classes as
        # something with tests to run
        if self.__class__.__dict__.get('abstract'):
            return
        else:
            return BaseTestCase.run(self, *args, **kwargs)

    def test_permissions_unauthenticated(self):
        """
        When the current SiteLocation requires logging in, unauthenticated
        users should be redirected to a login page.
        """
        self.site_location.submission_requires_login = True
        self.site_location.save()
        self.assertRequiresAuthentication(self.url)

    def test_permissions_authenticated(self):
        """
        If a user is logged in, but the button isn't displayed, they should
        only be allowed if they're an admin.
        """
        self.site_location.submission_requires_login = True
        self.site_location.display_submit_button = False
        self.site_location.save()

        self.assertRequiresAuthentication(self.url, self.GET_data,
                                          username='user', password='password')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, self.GET_data)
        self.assertEquals(response.status_code, 200)


class SecondStepSubmitBaseTestCase(SubmitVideoBaseTestCase):
    abstract = True
    template_name = None
    form_name = None

    def test_GET(self):
        """
        When the view is accessed via GET, it should render the
        self.template_name template, and get passed a self.form_name variable
        via the context.
        XXX The 'scraped_form' form should contain the name,
        description, thumbnail, tags, and URL from the scraped video.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.get(self.url, self.GET_data)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template.name,
                          self.template_name)
        self.assertTrue(self.form_name in response.context)

        submit_form = response.context[self.form_name]
        self.assertEquals(submit_form.initial['url'], self.POST_data['url'])
        self.assertEquals(submit_form.initial['tags'], self.POST_data['tags'])
        return submit_form

    def test_POST_fail(self):
        """
        If the POST to the view fails (the form doesn't validate, the template
        should be rerendered and include the form errors.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, self.GET_data)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template.name,
                          self.template_name)
        self.assertTrue(self.form_name in response.context)
        self.assertTrue(
            getattr(response.context[self.form_name], 'errors') is not None)

    def test_POST_succeed(self):
        """
        If the POST to the view succeeds, a new Video object should be created
        and the user should be redirected to the localtv_submit_thanks view.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, self.POST_data)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_submit_thanks')))

        video = models.Video.objects.all()[0]
        self.assertEquals(video.status, models.VIDEO_STATUS_UNAPPROVED)
        self.assertEquals(video.name, self.POST_data['name'])
        self.assertEquals(video.description, self.POST_data['description'])
        self.assertEquals(video.thumbnail_url, self.POST_data['thumbnail'])
        self.assertEquals(set(video.tags.values_list('name', flat=True)),
                          set(('tag1', 'tag2')))
        return video

    def test_POST_succeed_admin(self):
        """
        If the POST to the view succeeds and the user is an admin, the video
        should be automatically approved, and the user should be saved along
        with the video.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url, self.POST_data)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_submit_thanks')))

        video = models.Video.objects.all()[0]
        self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
        self.assertEquals(video.user, User.objects.get(username='admin'))


class SubmitVideoTestCase(SubmitVideoBaseTestCase):

    def setUp(self):
        SubmitVideoBaseTestCase.setUp(self)
        self.url = reverse('localtv_submit_video')

    def test_GET(self):
        """
        A GET request to the submit video page should render the
        'localtv/subsite/submit/submit_video.html' template, and get passed a
        'submit_form' in the context.
        """
        c = Client()
        response = c.get(self.url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template.name,
                          'localtv/subsite/submit/submit_video.html')
        self.assert_('submit_form' in response.context)

    def test_POST_fail_invalid_form(self):
        """
        If submitting the form fails, the template should be re-rendered with
        the form errors present.
        """
        c = Client()
        response = c.post(self.url,
                          {'url': 'not a URL'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template.name,
                          'localtv/subsite/submit/submit_video.html')
        self.assertTrue('submit_form' in response.context)
        self.assertTrue(getattr(
                response.context['submit_form'], 'errors') is not None)

    def test_POST_fail_existing_video_approved(self):
        """
        If the URL represents an approved video on the site, the form should be
        rerendered.  A 'was_duplicate' variable bound to True, and a 'video'
        variable bound to the Video object should be added to the context.
        """
        video = models.Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=models.VIDEO_STATUS_ACTIVE,
            website_url='http://www.pculture.org/')

        c = Client()
        response = c.post(self.url,
                          {'url': video.website_url})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template.name,
                          'localtv/subsite/submit/submit_video.html')
        self.assertTrue('submit_form' in response.context)
        self.assertTrue(response.context['was_duplicate'])
        self.assertEquals(response.context['video'], video)

    def test_POST_fail_existing_video_unapproved(self):
        """
        If the URL represents an unapproved video on the site, the form should
        be rerendered.  A 'was_duplicate' variable bound to True, and a 'video'
        variable bound to None should be added to the context.
        """
        video = models.Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=models.VIDEO_STATUS_UNAPPROVED,
            website_url='http://www.pculture.org/')

        c = Client()
        response = c.post(self.url,
                          {'url': video.website_url})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template.name,
                          'localtv/subsite/submit/submit_video.html')
        self.assertTrue('submit_form' in response.context)
        self.assertTrue(response.context['was_duplicate'])
        self.assertTrue(response.context['video'] is None)

    def test_POST_fail_existing_video_unapproved_admin(self):
        """
        If the URL represents an unapproved video on the site and the user is
        an admin, the video should be approved and the user should be
        redirected to the thanks page.
        """
        video = models.Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=models.VIDEO_STATUS_UNAPPROVED,
            website_url='http://www.pculture.org/')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url,
                          {'url': video.website_url})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_submit_thanks')))

        video = models.Video.objects.get(pk=video.pk)
        self.assertEquals(video.status,models.VIDEO_STATUS_ACTIVE)

    def test_POST_succeed_scraped(self):
        """
        If the URL represents a site that VidScraper understands, the user
        should be redirected to the scraped_submit_video view and include the
        tags.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, {
                'url': 'http://blip.tv/file/10',
                'tags': 'tag1, tag2'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                          "http://%s%s?%s" %(
                self.site_location.site.domain,
                reverse('localtv_submit_scraped_video'),
                urlencode({'url': 'http://blip.tv/file/10',
                           'tags': 'tag1, tag2'})))

    def test_POST_succeed_directlink(self):
        """
        If the URL represents a video file, the user should be redirected to
        the directlink_submit_video view and include the tags.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, {
                'url': ('http://blip.tv/file/get/'
                        'Miropcf-Miro20Introduction119.mp4'),
                'tags': 'tag1, tag2'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                          "http://%s%s?%s" %(
                self.site_location.site.domain,
                reverse('localtv_submit_directlink_video'),
                urlencode({'url': ('http://blip.tv/file/get/'
                                   'Miropcf-Miro20Introduction119.mp4'),
                           'tags': 'tag1, tag2'})))

    def test_POST_succeed_embedrequest(self):
        """
        If the URL isn't something we understand normally, the user should be
        redirected to the embedrequest_submit_video view and include the tags.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, {
                'url': 'http://pculture.org/',
                'tags': 'tag1, tag2'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                          "http://%s%s?%s" %(
                self.site_location.site.domain,
                reverse('localtv_submit_embedrequest_video'),
                urlencode({'url': 'http://pculture.org/',
                           'tags': 'tag1, tag2'})))


class ScrapedTestCase(SecondStepSubmitBaseTestCase):

    def setUp(self):
        SecondStepSubmitBaseTestCase.setUp(self)
        self.url = reverse('localtv_submit_scraped_video')
        self.template_name = 'localtv/subsite/submit/scraped_submit_video.html'
        self.form_name = 'scraped_form'
        self.POST_data = {
            'url': 'http://blip.tv/file/10',
            'name': 'name',
            'description': 'description',
            'thumbnail': 'http://www.getmiro.com/favicon.ico',
            'tags': 'tag1, tag2'
            }
        self.GET_data = {
            'url': self.POST_data['url'],
            'tags': self.POST_data['tags']
            }


    def test_GET(self):
        """
        In addition ot the SecondStepSubmitBaseTestCase.test_GET() assrtions,
        the form should have the name, description, and thumbnail set from the
        scraped data.
        """
        submit_form = SecondStepSubmitBaseTestCase.test_GET(self)
        self.assertEquals(submit_form.initial['name'], 'Fixing Otter')
        self.assertEquals(submit_form.initial['description'],
                          "<span><br>\n\n In my first produced vlog, I talk a "
                          "bit about breaking blip.tv, and fixing it.  The "
                          "audio's pretty bad, sorry about that.<br></span>")
        self.assertEquals(submit_form.initial['thumbnail'],
                          'http://a.images.blip.tv/'
                          '11156136631.95334664852457-424.jpg')

    def test_POST_succeed(self):
        """
        In addition ot the SecondStepSubmitBaseTestCase.test_POST_succeed()
        assrtions, the embed request video should have the website_url set to
        what was POSTed, and the file_url and embed_code set from the scraped
        data.
        """
        video = SecondStepSubmitBaseTestCase.test_POST_succeed(self)
        self.assertEquals(video.website_url, self.POST_data['url'])
        self.assertEquals(video.file_url,
                          'http://blip.tv/file/get/'
                          '11156136631.95334664852457.flv')
        self.assertEquals(video.embed_code,
                          '<embed src="http://blip.tv/play/g_5Qgm8C" '
                          'type="application/x-shockwave-flash" '
                          'width="480" height="390" '
                          'allowscriptaccess="always" allowfullscreen="true">'
                          '</embed>')


class DirectLinkTestCase(SecondStepSubmitBaseTestCase):

    def setUp(self):
        SecondStepSubmitBaseTestCase.setUp(self)
        self.url = reverse('localtv_submit_directlink_video')
        self.template_name = 'localtv/subsite/submit/direct_submit_video.html'
        self.form_name = 'direct_form'
        self.POST_data = {
            'url': ('http://blip.tv/file/get/'
                    'Miropcf-Miro20Introduction119.mp4'),
            'name': 'name',
            'description': 'description',
            'thumbnail': 'http://www.getmiro.com/favicon.ico',
            'website_url': 'http://www.getmiro.com/',
            'tags': 'tag1, tag2'
            }
        self.GET_data = {
            'url': self.POST_data['url'],
            'tags': self.POST_data['tags']
            }

    def test_POST_succeed(self):
        """
        In addition ot the SecondStepSubmitBaseTestCase.test_POST_succeed()
        assrtions, the embed request video should have the website_url and
        file_url set to what was POSTed.
        """
        video = SecondStepSubmitBaseTestCase.test_POST_succeed(self)
        self.assertEquals(video.website_url, self.POST_data['website_url'])
        self.assertEquals(video.file_url, self.POST_data['url'])
        self.assertEquals(video.embed_code, '')


class EmbedRequestTestCase(SecondStepSubmitBaseTestCase):

    def setUp(self):
        SecondStepSubmitBaseTestCase.setUp(self)
        self.url = reverse('localtv_submit_embedrequest_video')
        self.template_name = 'localtv/subsite/submit/embed_submit_video.html'
        self.form_name = 'embed_form'
        self.POST_data = {
            'url': 'http://www.pculture.org/',
            'name': 'name',
            'description': 'description',
            'thumbnail': 'http://www.getmiro.com/favicon.ico',
            'website_url': 'http://www.getmiro.com/',
            'embed': '<h1>hi!</h1>',
            'tags': 'tag1, tag2'
            }
        self.GET_data = {
            'url': self.POST_data['url'],
            'tags': self.POST_data['tags']
            }

    def test_POST_succeed(self):
        """
        In addition ot the SecondStepSubmitBaseTestCase.test_POST_succeed()
        assrtions, the embed request video should have the website_url and
        embed_code set to what was POSTed.
        """
        video = SecondStepSubmitBaseTestCase.test_POST_succeed(self)
        self.assertEquals(video.website_url, self.POST_data['website_url'])
        self.assertEquals(video.file_url, '')
        self.assertEquals(video.embed_code, self.POST_data['embed'])


# -----------------------------------------------------------------------------
# Feed tests
# -----------------------------------------------------------------------------

class MockVidScraper(object):

    errors = vidscraper.errors

    def auto_scrape(self, link, fields=None):
        raise vidscraper.errors.Error('could not scrape %s' % link)

class FeedModelTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['feed']

    def setUp(self):
        BaseTestCase.setUp(self)
        self.vidscraper = models.vidscraper
        models.vidscraper = MockVidScraper()

    def tearDown(self):
        BaseTestCase.tearDown(self)
        models.vidscraper = self.vidscraper
        del self.vidscraper

    def _data_file(self, filename):
        return os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                'testdata',
                filename))

    def test_auto_approve_True(self):
        """
        If Feed.auto_approve is True, the imported videos should be marked as
        active.
        """
        feed = models.Feed.objects.get()
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
        feed = models.Feed.objects.get()
        feed.auto_approve = False
        feed.feed_url = self._data_file('feed.rss')
        feed.update_items()
        self.assertEquals(models.Video.objects.count(), 5)
        self.assertEquals(models.Video.objects.filter(
                status=models.VIDEO_STATUS_UNAPPROVED).count(), 5)

    def test_entries_inserted_in_reverse_order(self):
        """
        When adding entries from a feed, they should be added to the database
        in rever order (oldest first)
        """
        feed = models.Feed.objects.get()
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
        feed = models.Feed.objects.get()
        feed.feed_url = self._data_file('feed_with_duplicate_guid.rss')
        feed.update_items()
        self.assertEquals(models.Video.objects.count(), 1)
        self.assertEquals(models.Video.objects.get().name, 'Old Item')

    def test_ignore_duplicate_link(self):
        """
        If the GUID already exists for this feed, the newer item should be
        skipped.
        """
        feed = models.Feed.objects.get()
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
        """
        feed = models.Feed.objects.get()
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
        self.assertEquals(video.file_url_mimetype, 'video/vnd.objectvideo')
        self.assertTrue(video.has_thumbnail)
        self.assertEquals(video.thumbnail_url,
                          'http://e.static.blip.tv/'
                          'Miropcf-DaveGlasscoSupportsMiro959.jpg')
        self.assertEquals(video.when_published,
                          datetime.datetime(2008, 3, 27, 23, 25, 51))
        self.assertEquals(video.video_service(), 'blip.tv')

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

        feed = models.Feed.objects.get()
        for service, url in services:
            feed.feed_url = url
            self.assertEquals(feed.video_service(), service,
                              '%s was incorrectly described as %s' %
                              (url, feed.video_service()))

