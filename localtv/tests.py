import datetime
import os.path
from urllib import quote_plus, urlencode

import feedparser
import vidscraper

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import File
from django.core.paginator import Page
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from django.utils.encoding import force_unicode

from localtv import models
from localtv.subsite.admin import forms as admin_forms
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
        for user in User.objects.all():
            try:
                profile = user.get_profile()
            except models.Profile.DoesNotExist:
                pass
            else:
                if profile.logo:
                    profile.logo.delete()

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

    @staticmethod
    def _POST_data_from_formset(formset, **kwargs):
        """
        This method encapsulates the logic to turn a Formset object into a
        dictionary of data that can be sent to a view.
        """
        POST_data = {
            'form-TOTAL_FORMS': formset.total_form_count(),
            'form-INITIAL_FORMS': formset.initial_form_count()}

        for index, form in enumerate(formset.forms):
            for name, field in form.fields.items():
                data = form.initial.get(name, field.initial)
                if callable(data):
                    data = data()
                if isinstance(field, admin_forms.SourceChoiceField):
                    if data is not None:
                        data = '%s-%s' % (data.__class__.__name__.lower(),
                                          data.pk)
                if isinstance(data, (list, tuple)):
                    data = [force_unicode(item) for item in data]
                elif data:
                    data = force_unicode(data)
                if data:
                    POST_data[form.add_prefix(name)] = data
        POST_data.update(kwargs)
        return POST_data


# -----------------------------------------------------------------------------
# Video submit tests
# -----------------------------------------------------------------------------

class SubmitVideoBaseTestCase(BaseTestCase):
    abstract = True
    url = None
    GET_data = {}

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
        self.assertStatusCodeEquals(response, 200)


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
        self.assertStatusCodeEquals(response, 200)
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
        self.assertStatusCodeEquals(response, 200)
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
        self.assertStatusCodeEquals(response, 302)
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
        self.assertStatusCodeEquals(response, 302)
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
        self.assertStatusCodeEquals(response, 200)
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
        self.assertStatusCodeEquals(response, 200)
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
        self.assertStatusCodeEquals(response, 200)
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
        self.assertStatusCodeEquals(response, 200)
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
        self.assertStatusCodeEquals(response, 302)
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
        self.assertStatusCodeEquals(response, 302)
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
        self.assertStatusCodeEquals(response, 302)
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
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          "http://%s%s?%s" %(
                self.site_location.site.domain,
                reverse('localtv_submit_embedrequest_video'),
                urlencode({'url': 'http://pculture.org/',
                           'tags': 'tag1, tag2'})))

    def test_POST_succeed_canonical(self):
        """
        If the URL is a scraped video but the URL we were given is not the
        canonical URL for that video, the user should be redirected as normal,
        but with the canonical URL.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        youtube_url = 'http://www.youtube.com/watch?v=AfsZzeNF8A4'
        response = c.post(self.url, {
                'url': youtube_url + '&feature=player_embedded',
                'tags': 'tag1, tag2'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          "http://%s%s?%s" %(
                self.site_location.site.domain,
                reverse('localtv_submit_scraped_video'),
                urlencode({'url': youtube_url,
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

        feed = models.Feed.objects.get(pk=1)
        for service, url in services:
            feed.feed_url = url
            self.assertEquals(feed.video_service(), service,
                              '%s was incorrectly described as %s' %
                              (url, feed.video_service()))


# -----------------------------------------------------------------------------
# Approve/reject video tests
# -----------------------------------------------------------------------------


class AdministrationBaseTestCase(BaseTestCase):

    abstract = True

    def test_authentication(self):
        """
        This view should only be visible to administrators.
        """
        self.assertRequiresAuthentication(self.url)

        self.assertRequiresAuthentication(self.url,
                                          username='user', password='password')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)


class ApproveRejectAdministrationTestCase(AdministrationBaseTestCase):

    fixtures = BaseTestCase.fixtures + ['videos']

    url = reverse('localtv_admin_approve_reject')

    def test_GET(self):
        """
        A GET request to the approve/reject view should render the
        'localtv/subsite/admin/approve_reject_table.html' template.  The
        context should include 'current_video' (the first Video object),
        'page_obj' (a Django Page object), and 'video_list' (a list of the
        Video objects on the current page).
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/approve_reject_table.html')
        self.assertIsInstance(response.context['current_video'],
                              models.Video)
        self.assertIsInstance(response.context['page_obj'],
                              Page)
        video_list = response.context['video_list']
        self.assertEquals(video_list[0], response.context['current_video'])
        self.assertEquals(len(video_list), 10)

    def test_GET_with_page(self):
        """
        A GET request ot the approve/reject view with a 'page' GET argument
        should return that page of the videos to be approved/rejected.  The
        first page is the 10 oldest videos, the second page is the next 10,
        etc.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED).order_by(
            'when_submitted', 'when_published')
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        page1_response = c.get(self.url,
                               {'page': '1'})
        self.assertEquals(list(response.context['video_list']),
                          list(page1_response.context['video_list']))
        self.assertEquals(list(page1_response.context['video_list']),
                          list(unapproved_videos[:10]))
        page2_response = c.get(self.url,
                               {'page': '2'})
        self.assertNotEquals(page1_response, page2_response)
        self.assertEquals(list(page2_response.context['video_list']),
                          list(unapproved_videos[10:20]))
        page3_response = c.get(self.url,
                               {'page': '3'}) # doesn't exist, should return
                                              # page 2
        self.assertEquals(list(page2_response.context['video_list']),
                          list(page3_response.context['video_list']))

    def test_GET_preview(self):
        """
        A GET request to the preview_video view should render the
        'localtv/subsite/admin/video_preview.html' template and have a
        'current_video' in the context.  The current_video should be the video
        with the primary key passed in as GET['video_id'].
        """
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)[0]
        url = reverse('localtv_admin_preview_video')
        self.assertRequiresAuthentication(url, {'video_id': str(video.pk)})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url,
                         {'video_id': str(video.pk)})
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/video_preview.html')
        self.assertEquals(response.context['current_video'],
                          video)

    def test_GET_approve(self):
        """
        A GET request to the approve_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].
        """
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)[0]
        url = reverse('localtv_admin_approve_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        video = models.Video.objects.get(pk=video.pk) # reload
        self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
        self.assertTrue(video.when_approved is not None)
        self.assertTrue(video.last_featured is None)

    def test_GET_approve_with_feature(self):
        """
        A GET request to the approve_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].  When 'feature' is present in the GET arguments, the
        video should also be featured.
        """
        # XXX why do we have this function
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)[0]
        url = reverse('localtv_admin_approve_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk,
                                                'feature': 'yes'})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk),
                               'feature': 'yes'},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        video = models.Video.objects.get(pk=video.pk) # reload
        self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
        self.assertTrue(video.when_approved is not None)
        self.assertTrue(video.last_featured is not None)

    def test_GET_reject(self):
        """
        A GET request to the reject_video view should reject the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].
        """
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)[0]
        url = reverse('localtv_admin_reject_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        video = models.Video.objects.get(pk=video.pk) # reload
        self.assertEquals(video.status, models.VIDEO_STATUS_REJECTED)
        self.assertTrue(video.last_featured is None)

    def test_GET_feature(self):
        """
        A GET request to the feature_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].  If the video is unapproved, it should become
        approved.
        """
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)[0]
        url = reverse('localtv_admin_feature_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        video = models.Video.objects.get(pk=video.pk) # reload
        self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
        self.assertTrue(video.when_approved is not None)
        self.assertTrue(video.last_featured is not None)

    def test_GET_unfeature(self):
        """
        A GET request to the unfeature_video view should unfeature the video
        and redirect back to the referrer.  The video should be specified by
        GET['video_id'].  The video status is not affected.
        """
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_ACTIVE).exclude(
            last_featured=None)[0]

        url = reverse('localtv_admin_unfeature_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        video = models.Video.objects.get(pk=video.pk) # reload
        self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
        self.assertTrue(video.last_featured is None)

    def test_GET_reject_all(self):
        """
        A GET request to the reject_all view should reject all the videos on
        the given page and redirect back to the referrer.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)
        page2_videos = unapproved_videos[10:20]

        url = reverse('localtv_admin_reject_all')
        self.assertRequiresAuthentication(url, {'page': 2})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'page': 2},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        for video in page2_videos:
            self.assertEquals(video.status, models.VIDEO_STATUS_REJECTED)

    def test_GET_approve_all(self):
        """
        A GET request to the reject_all view should approve all the videos on
        the given page and redirect back to the referrer.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)
        page2_videos = unapproved_videos[10:20]

        url = reverse('localtv_admin_approve_all')
        self.assertRequiresAuthentication(url, {'page': 2})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'page': 2},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        for video in page2_videos:
            self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
            self.assertTrue(video.when_approved is not None)


    def test_GET_clear_all(self):
        """
        A GET request to the clear_all view should render the
        'localtv/subsite/admin/clear_confirm.html' and have a 'videos' variable
        in the context which is a list of all the unapproved videos.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)
        unapproved_videos_count = unapproved_videos.count()

        url = reverse('localtv_admin_clear_all')
        self.assertRequiresAuthentication(url)

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/clear_confirm.html')
        self.assertEquals(list(response.context['videos']),
                          list(unapproved_videos))

        # nothing was rejected
        self.assertEquals(models.Video.objects.filter(
                status=models.VIDEO_STATUS_UNAPPROVED).count(),
                          unapproved_videos_count)

    def test_POST_clear_all_failure(self):
        """
        A POST request to the clear_all view without POST['confirm'] = 'yes'
        should render the 'localtv/subsite/admin/clear_confirm.html' template
        and have a 'videos' variable in the context which is a list of all the
        unapproved videos.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)
        unapproved_videos_count = unapproved_videos.count()

        url = reverse('localtv_admin_clear_all')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/clear_confirm.html')
        self.assertEquals(list(response.context['videos']),
                          list(unapproved_videos))

        # nothing was rejected
        self.assertEquals(models.Video.objects.filter(
                status=models.VIDEO_STATUS_UNAPPROVED).count(),
                          unapproved_videos_count)

    def test_POST_clear_all_succeed(self):
        """
        A POST request to the clear_all view with POST['confirm'] = 'yes'
        should reject all the videos and redirect to the approve_reject view.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)
        unapproved_videos_count = unapproved_videos.count()

        rejected_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_REJECTED)
        rejected_videos_count = rejected_videos.count()

        url = reverse('localtv_admin_clear_all')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url, {'confirm': 'yes'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_admin_approve_reject')))

        # all the unapproved videos are now rejected
        self.assertEquals(models.Video.objects.filter(
                status=models.VIDEO_STATUS_REJECTED).count(),
                          unapproved_videos_count + rejected_videos_count)


# -----------------------------------------------------------------------------
# Sources administration tests
# -----------------------------------------------------------------------------


class SourcesAdministrationTestCase(AdministrationBaseTestCase):

    fixtures = AdministrationBaseTestCase.fixtures + [
        'feeds', 'savedsearches', 'videos', 'categories']

    url = reverse('localtv_admin_manage_page')

    def test_GET(self):
        """
        A GET request to the manage_sources view should return a paged view of
        the sources (feeds and saved searches), sorted in alphabetical order.
        It should render the 'localtv/subsite/admin/manage_sources.html'
        template.

        Variables in the context include:

        * add_feed_form (a form to add a new feed)
        * page (a Page object for the current page)
        * headers (a list of headers to display)
        * search_string (the search string we're using to filter sources)
        * source_filter (the type of source to show)
        * categories (a QuerySet of the current categories)
        * users (a QuerySet of the current users)
        * successful (True if the last operation was successful)
        * formset (the FormSet for the sources on this page)
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/manage_sources.html')
        self.assertTrue('add_feed_form' in response.context[0])
        self.assertTrue('page' in response.context[0])
        self.assertTrue('headers' in response.context[0])
        self.assertEquals(response.context[0]['search_string'], '')
        self.assertTrue(response.context[0]['source_filter'] is None)
        self.assertEquals(response.context[0]['categories'].model,
                          models.Category)
        self.assertTrue(response.context[0]['users'].model, User)
        self.assertTrue('successful' in response.context[0])
        self.assertTrue('formset' in response.context[0])

        page = response.context['page']
        self.assertEquals(len(page.object_list), 15)
        self.assertEquals(list(sorted(page.object_list,
                                      key=lambda x:unicode(x).lower())),
                          page.object_list)

    def test_GET_sorting(self):
        """
        A GET request with a 'sort' key in the GET request should sort the
        sources by that field.  The default sort should be by the lower-case
        name of the source.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      key=lambda x:unicode(x).lower())),
                          page.object_list)

        # reversed name
        response = c.get(self.url, {'sort': '-name__lower'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:unicode(x).lower())),
                          page.object_list)

        # auto approve
        response = c.get(self.url, {'sort': 'auto_approve'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      key=lambda x:x.auto_approve)),
                          page.object_list)

        # reversed auto_approve
        response = c.get(self.url, {'sort': '-auto_approve'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:x.auto_approve)),
                          page.object_list)

        # type (feed, search, user)
        response = c.get(self.url, {'sort': 'type'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      key=lambda x:x.source_type().lower())),
                          page.object_list)

        # reversed type (user, search, feed)
        response = c.get(self.url, {'sort': '-type'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:x.source_type().lower())),
                          page.object_list)

    def test_GET_filtering(self):
        """
        A GET request with a 'filter' key in the GET request should filter the
        sources to feeds/users/searches.
        """

        c = Client()
        c.login(username='admin', password='admin')

        # search filter
        response = c.get(self.url, {'filter': 'search'})
        page = response.context['page']
        self.assertEquals(
            list(page.object_list),
            list(models.SavedSearch.objects.extra({
                        'name__lower': 'LOWER(query_string)'}).order_by(
                    'name__lower')[:10]))

        # feed filter (ignores feeds that represent video service users)
        response = c.get(self.url, {'filter': 'feed'})
        page = response.context['page']
        self.assertEquals(len(page.object_list), 6)
        for feed in page.object_list:
            self.assertTrue(feed.video_service() is None)

        # user filter (only includes feeds that represent video service users)
        response = c.get(self.url, {'filter': 'user'})
        page = response.context['page']
        self.assertEquals(len(page.object_list), 4)
        for feed in page.object_list:
            self.assertTrue(feed.video_service() is not None)

    def test_POST_failure(self):
        """
        A POST request to the manage_sources view with an invalid formset
        should cause the page to be rerendered and include the form errors.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data_invalid = POST_data.copy()
        del POST_data_invalid['form-0-name'] # don't include some mandatory
                                             # fields
        del POST_data_invalid['form-0-feed_url']
        del POST_data_invalid['form-1-query_string']

        POST_response = c.post(self.url, POST_data_invalid)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertTrue(POST_response.context['formset'].is_bound)
        self.assertFalse(POST_response.context['formset'].is_valid())
        self.assertEquals(len(POST_response.context['formset'].errors[0]), 2)
        self.assertEquals(len(POST_response.context['formset'].errors[1]), 1)

        # make sure the data hasn't changed
        self.assertEquals(POST_data,
                          self._POST_data_from_formset(
                POST_response.context['formset']))

    def test_POST_succeed(self):
        """
        A POST request to the manage_sources view with a valid formset should
        save the updated models and redirect to the same URL with a
        'successful' field in the GET query.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data.update({
                'form-0-name': 'new name!',
                'form-0-feed_url': 'http://pculture.org/',
                'form-0-webpage': 'http://getmiro.com/',
                'form-1-query_string': 'localtv'})

        POST_response = c.post(self.url, POST_data,
                               follow=True)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEquals(POST_response.redirect_chain,
                          [('http://%s%s?successful' % (
                        self.site_location.site.domain,
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

        # make sure the data has been updated
        feed = models.Feed.objects.get(pk=POST_data['form-0-id'].split('-')[1])
        self.assertEquals(feed.name, POST_data['form-0-name'])
        self.assertEquals(feed.feed_url, POST_data['form-0-feed_url'])
        self.assertEquals(feed.webpage, POST_data['form-0-webpage'])

        search = models.SavedSearch.objects.get(
            pk=POST_data['form-1-id'].split('-')[1])
        self.assertEquals(search.query_string,
                          POST_data['form-1-query_string'])


    def test_POST_succeed_with_page(self):
        """
        A POST request to the manage_sources view with a valid formset should
        save the updated models and redirect to the same URL with a
        'successful' field in the GET query, even with a 'page' argument in the
        query string of the POST request.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'page': 2})
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_response = c.post(self.url+"?page=2", POST_data,
                               follow=True)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEquals(POST_response.redirect_chain,
                          [('http://%s%s?page=2&successful' % (
                        self.site_location.site.domain,
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

    def test_POST_delete(self):
        """
        A POST request to the manage sources view with a valid formset and a
        DELETE value for a source should remove that source along with all of
        its videos.`
        """
        feed = models.Feed.objects.get(pk=3)
        saved_search = models.SavedSearch.objects.get(pk=8)

        for v in models.Video.objects.all()[:5]:
            v.feed = feed
            v.save()

        for v in models.Video.objects.all()[5:10]:
            v.search = saved_search
            v.save()

        video_count = models.Video.objects.count()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)
        POST_data['form-0-DELETE'] = 'yes'
        POST_data['form-1-DELETE'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        self.assertEquals(
            models.Feed.objects.filter(pk=3).count(), # form 0
            0)

        self.assertEquals(
            models.SavedSearch.objects.filter(pk=8).count(), # form 1
            0)

        # make sure the 10 videos got removed
        self.assertEquals(models.Video.objects.count(),
                          video_count - 10)

    def test_POST_bulk_edit(self):
        """
        A POST request to the manage_sources view with a valid formset and the
        extra form filled out should update any source with the bulk option
        checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['form-15-auto_categories'] = [1, 2]
        POST_data['form-15-auto_authors'] = [1, 2]
        POST_data['form-15-auto_approve'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        feed = models.Feed.objects.get(pk=3) # form 0
        saved_search = models.SavedSearch.objects.get(pk=8) # form 1

        self.assertEquals(feed.auto_approve, True)
        self.assertEquals(saved_search.auto_approve, True)
        self.assertEquals(
            set(feed.auto_categories.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEquals(
            set(saved_search.auto_categories.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEquals(
            set(feed.auto_authors.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEquals(
            set(saved_search.auto_authors.values_list('pk', flat=True)),
            set([1, 2]))

    def test_POST_bulk_delete(self):
        """
        A POST request to the manage_sources view with a valid formset and a
        POST['bulk_action'] of 'remove' should remove the videos with the bulk
        option checked.
        """
        feed = models.Feed.objects.get(pk=3)
        saved_search = models.SavedSearch.objects.get(pk=8)

        for v in models.Video.objects.all()[:5]:
            v.feed = feed
            v.save()

        for v in models.Video.objects.all()[5:10]:
            v.search = saved_search
            v.save()

        video_count = models.Video.objects.count()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['bulk_action'] = 'remove'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        self.assertEquals(
            models.Feed.objects.filter(pk=3).count(), # form 0
            0)

        self.assertEquals(
            models.SavedSearch.objects.filter(pk=8).count(), # form 1
            0)

        # make sure the 10 videos got removed
        self.assertEquals(models.Video.objects.count(),
                          video_count - 10)

    def test_POST_switching_categories_authors(self):
        """
        A POST request to the manage_sources view with a valid formset that
        includes changed categories or authors, videos that had the old
        categories/authors should be updated to the new values.
        """
        feed = models.Feed.objects.get(pk=3)
        saved_search = models.SavedSearch.objects.get(pk=8)
        category = models.Category.objects.get(pk=1)
        user = User.objects.get(pk=1)
        category2 = models.Category.objects.get(pk=2)
        user2 = User.objects.get(pk=2)

        for v in models.Video.objects.order_by('pk')[:3]:
            v.feed = feed
            if v.pk == 1:
                v.categories.add(category)
                v.authors.add(user)
            elif v.pk == 2:
                v.categories.add(category)
            elif v.pk == 3:
                v.authors.add(user)
            else:
                self.fail('invalid feed pk: %i' % v.pk)
            v.save()

        for v in models.Video.objects.order_by('pk')[3:6]:
            v.search = saved_search
            if v.pk == 4:
                v.categories.add(category)
                v.authors.add(user)
            elif v.pk == 5:
                v.categories.add(category)
            elif v.pk == 6:
                v.authors.add(user)
            else:
                self.fail('invalid search pk: %i' % v.pk)
            v.save()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        for i in range(2):
            POST_data['form-%i-bulk'% i] = 'yes'
        POST_data['form-15-auto_categories'] = [category2.pk]
        POST_data['form-15-auto_authors'] = [user2.pk]

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        for v in models.Video.objects.order_by('pk')[:3]:
            self.assertEquals(v.feed, feed)
            if v.pk == 1:
                # nothing changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user]))
            elif v.pk == 2:
                # user changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user2]))
            elif v.pk == 3:
                # category changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category2]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user]))
            else:
                self.fail('invalid feed video pk: %i' % v.pk)

        for v in models.Video.objects.order_by('pk')[3:6]:
            self.assertEquals(v.search, saved_search)
            if v.pk == 4:
                # nothing changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user]))
            elif v.pk == 5:
                # user changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user2]))
            elif v.pk == 6:
                # category changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category2]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user]))
            else:
                self.fail('invalid search video pk: %i' % v.pk)


# -----------------------------------------------------------------------------
# Feed Administration tests
# -----------------------------------------------------------------------------


class FeedAdministrationTestCase(BaseTestCase):

    url = reverse('localtv_admin_feed_add')
    feed_url = "http://participatoryculture.org/feeds_test/feed7.rss"

    def test_authentication_done(self):
        """
        The localtv_admin_feed_add_done view should require administration
        priviledges.
        """
        url = reverse('localtv_admin_feed_add_done', args=[1])
        self.assertRequiresAuthentication(url)

        self.assertRequiresAuthentication(url,
                                          username='user', password='password')

    def test_GET(self):
        """
        A GET request to the add_feed view should render the
        'localtv/subsite/admin/add_feed.html' template.  Context:

        * form: a SourceForm to allow setting auto categories/authors
        * video_count: the number of videos we think we can get out of the feed
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'feed_url': self.feed_url})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[2].name,
                          'localtv/subsite/admin/add_feed.html')
        self.assertTrue(response.context[2]['form'].instance.feed_url,
                        self.feed_url)
        self.assertEquals(response.context[2]['video_count'], 1)

    def test_POST_failure(self):
        """
        A POST request to the add_feed view should rerender the template with
        the form incluing the errors.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url + "?feed_url=%s" % self.feed_url,
                          {'feed_url': self.feed_url,
                           'auto_categories': [1]})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/add_feed.html')
        self.assertTrue(response.context[0]['form'].instance.feed_url,
                        self.feed_url)
        self.assertFalse(response.context[0]['form'].is_valid())
        self.assertEquals(response.context[0]['video_count'], 1)

    def test_POST_cancel(self):
        """
        A POST request to the add_feed view with POST['cancel'] set should
        redirect the user to the localtv_admin_manage_page view.  No objects
        should be created.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url + "?feed_url=%s" % self.feed_url,
                          {'feed_url': self.feed_url,
                           'auto_approve': 'yes',
                           'cancel': 'yes'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_admin_manage_page')))

        self.assertEquals(models.Feed.objects.count(), 0)

    def test_POST_succeed(self):
        """
        A POST request to the add_feed view with a valid form should redirect
        the user to the localtv_admin_add_feed_done view.

        A Feed object should also be created, but not have any items.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url + "?feed_url=%s" % self.feed_url,
                          {'feed_url': self.feed_url,
                           'auto_approve': 'yes'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_admin_feed_add_done', args=[1])))

        feed = models.Feed.objects.get()
        self.assertEquals(feed.name, 'Valid Feed with Relative Links')
        self.assertEquals(feed.feed_url, self.feed_url)
        self.assertTrue(feed.auto_approve)

    def test_GET_done(self):
        """
        A GET request to the add_feed_done view should import videos from the
        given feed.  It should also render the
        'localtv/subsite/admin/feed_done.html' template and have a 'feed'
        variable in the context pointing to the Feed object.
        """
        c = Client()
        c.login(username='admin', password='admin')
        c.post(self.url + "?feed_url=%s" % self.feed_url,
               {'feed_url': self.feed_url,
                'auto_approve': 'yes'})

        response = c.get(reverse('localtv_admin_feed_add_done', args=[1]))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[2].name,
                          'localtv/subsite/admin/feed_done.html')
        feed = models.Feed.objects.get()
        self.assertEquals(response.context[2]['feed'], feed)
        self.assertEquals(feed.video_set.count(), 1)

        video = feed.video_set.all()[0]
        self.assertEquals(video.status,
                          models.VIDEO_STATUS_ACTIVE)
        self.assertEquals(video.thumbnail_url,
                          ('http://participatoryculture.org/feeds_test/'
                           'mike_tv_drawing_cropped.jpg'))
        self.assertEquals(video.file_url,
                          ('http://participatoryculture.org/feeds_test/'
                           'py1.mov'))
        self.assertEquals(video.file_url_mimetype, 'video/quicktime')
        self.assertEquals(video.file_url_length, 842)

    def test_GET_auto_approve(self):
        """
        A GET request to the feed_auto_approve view should set the auto_approve
        bit on the feed specified in the URL and redirect back to the referrer.
        It should also require the user to be an administrator.
        """
        feed = models.Feed.objects.create(site=self.site_location.site,
                                          name='name',
                                          feed_url='feed_url',
                                          auto_approve=False,
                                          last_updated=datetime.datetime.now(),
                                          status=models.FEED_STATUS_ACTIVE)
        url = reverse('localtv_admin_feed_auto_approve', args=(feed.pk,))
        self.assertRequiresAuthentication(url)
        self.assertRequiresAuthentication(url,
                                          username='user',
                                          password='password')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url,
                         HTTP_REFERER='http://www.google.com/')
        self.assertEquals(feed.auto_approve, False)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'], 'http://www.google.com/')

    def test_GET_auto_approve_disable(self):
        """
        A GET request to the feed_auto_approve view with GET['disable'] set
        should remove the auto_approve bit on the feed specified in the URL and
        redirect back to the referrer.
        """
        feed = models.Feed.objects.create(site=self.site_location.site,
                                          name='name',
                                          feed_url='feed_url',
                                          auto_approve=True,
                                          last_updated=datetime.datetime.now(),
                                          status=models.FEED_STATUS_ACTIVE)
        url = reverse('localtv_admin_feed_auto_approve', args=(feed.pk,))

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'disable': 'yes'},
                         HTTP_REFERER='http://www.google.com/')
        self.assertEquals(feed.auto_approve, True)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'], 'http://www.google.com/')


# -----------------------------------------------------------------------------
# Search administration tests
# -----------------------------------------------------------------------------


class SearchAdministrationTestCase(AdministrationBaseTestCase):

    url = reverse('localtv_admin_search')

    def test_GET(self):
        """
        A GET request to the livesearch view should render the
        'localtv/subsite/admin/livesearch_table.html' template.  Context:

        * current_video: a Video object for the video to display
        * page_obj: a Page object for the current page of results
        * query_string: the search query
        * order_by: 'relevant' or 'latest'
        * is_saved_search: True if the query was already saved
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/livesearch_table.html')
        self.assertTrue('current_video' in response.context[0])
        self.assertTrue('page_obj' in response.context[0])
        self.assertTrue('query_string' in response.context[0])
        self.assertTrue('order_by' in response.context[0])
        self.assertTrue('is_saved_search' in response.context[0])

    def test_GET_query(self):
        """
        A GET request to the livesearch view and GET['query'] argument should
        list some videos that match the query.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'query': 'search string'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[2].name,
                          'localtv/subsite/admin/livesearch_table.html')
        self.assertIsInstance(response.context[2]['current_video'],
                              util.MetasearchVideo)
        self.assertEquals(response.context[2]['page_obj'].number, 1)
        self.assertEquals(len(response.context[2]['page_obj'].object_list), 10)
        self.assertEquals(response.context[2]['query_string'], 'search string')
        self.assertEquals(response.context[2]['order_by'], 'latest')
        self.assertEquals(response.context[2]['is_saved_search'], False)

    def test_GET_query_pagination(self):
        """
        A GET request to the livesearch view with GET['query'] and GET['page']
        arguments should return another page of results.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'query': 'search string'})
        self.assertEquals(response.context[2]['page_obj'].number, 1)
        self.assertEquals(len(response.context[2]['page_obj'].object_list), 10)

        response2 = c.get(self.url,
                         {'query': 'search string',
                          'page': '2'})
        self.assertEquals(response2.context[2]['page_obj'].number, 2)
        self.assertEquals(len(response2.context[2]['page_obj'].object_list),
                          10)

        self.assertNotEquals([v.id for v in
                              response.context[2]['page_obj'].object_list],
                             [v.id for v in
                              response2.context[2]['page_obj'].object_list])


    def test_GET_approve(self):
        """
        A GET request to the approve view should create a new video object from
        the search and redirect back to the referrer.  The video should be
        removed from subsequent search listings.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'query': 'search string'})
        metasearch_video = response.context[2]['page_obj'].object_list[0]
        metasearch_video2 = response.context[2]['page_obj'].object_list[1]

        response = c.get(reverse('localtv_admin_search_video_approve'),
                         {'query': 'search string',
                          'video_id': metasearch_video.id},
                         HTTP_REFERER="http://www.getmiro.com/")
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'], "http://www.getmiro.com/")

        v = models.Video.objects.get()
        self.assertEquals(v.site, self.site_location.site)
        self.assertEquals(v.name, metasearch_video.name)
        self.assertEquals(v.description, metasearch_video.description)
        self.assertEquals(v.file_url, metasearch_video.file_url)
        self.assertEquals(v.embed_code, metasearch_video.embed_code)
        self.assertTrue(v.last_featured is None)

        response = c.get(self.url,
                         {'query': 'search string'})
        self.assertEquals(response.context[2]['page_obj'].object_list[0].id,
                          metasearch_video2.id)

    def test_GET_approve_feature(self):
        """
        A GET request to the approve view should create a new video object from
        the search and redirect back to the referrer.  If GET['feature'] is
        present, the video should also be marked as featured.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'query': 'search string'})
        metasearch_video = response.context[2]['page_obj'].object_list[0]

        response = c.get(reverse('localtv_admin_search_video_approve'),
                         {'query': 'search string',
                          'feature': 'yes',
                          'video_id': metasearch_video.id},
                         HTTP_REFERER="http://www.getmiro.com/")
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'], "http://www.getmiro.com/")

        v = models.Video.objects.get()
        self.assertTrue(v.last_featured is not None)

    def test_GET_display(self):
        """
        A GET request to the display view should render the
        'localtv/subsite/admin/video_preview.html' and include the
        MetasearchVideo as 'current_video' in the context.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'query': 'search string'})
        metasearch_video = response.context[2]['page_obj'].object_list[0]

        response = c.get(reverse('localtv_admin_search_video_display'),
                         {'query': 'search string',
                          'video_id': metasearch_video.id})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/video_preview.html')
        self.assertEquals(response.context[0]['current_video'].id,
                          metasearch_video.id)

    def test_GET_create_saved_search(self):
        """
        A GET request to the create_saved_search view should create a new
        SavedSearch object and redirect back to the referrer.  Requests to the
        livesearch view should then indicate that this search is saved.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_admin_search_add'),
                         {'query': 'search string'},
                         HTTP_REFERER='http://www.getmiro.com/')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'], 'http://www.getmiro.com/')

        saved_search = models.SavedSearch.objects.get()
        self.assertEquals(saved_search.query_string, 'search string')
        self.assertEquals(saved_search.site, self.site_location.site)
        self.assertEquals(saved_search.user.username, 'admin')

        response = c.get(self.url,
                         {'query': 'search string'})
        self.assertTrue(response.context[2]['is_saved_search'])

    def test_GET_search_auto_approve(self):
        """
        A GET request to the search_auto_appprove view should set the
        auto_approve bit to True on the given SavedSearch object and redirect
        back to the referrer
        """
        saved_search = models.SavedSearch.objects.create(
            site=self.site_location.site,
            query_string='search string')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_admin_search_auto_approve',
                                 args=[saved_search.pk]),
                         HTTP_REFERER='http://www.getmiro.com/')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://www.getmiro.com/')

        saved_search = models.SavedSearch.objects.get(pk=saved_search.pk)
        self.assertTrue(saved_search.auto_approve)

    def test_GET_search_auto_approve_disable(self):
        """
        A GET request to the search_auto_appprove view with GET['disable'] set
        should set the auto_approve bit to False on the given SavedSearch
        object and redirect back to the referrer
        """
        saved_search = models.SavedSearch.objects.create(
            site=self.site_location.site,
            auto_approve=True,
            query_string='search string')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_admin_search_auto_approve',
                                 args=[saved_search.pk]),
                                 {'disable': 'yes'},
                         HTTP_REFERER='http://www.getmiro.com/')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://www.getmiro.com/')

        saved_search = models.SavedSearch.objects.get(pk=saved_search.pk)
        self.assertFalse(saved_search.auto_approve)


# -----------------------------------------------------------------------------
# User administration tests
# -----------------------------------------------------------------------------


class UserAdministrationTestCase(AdministrationBaseTestCase):

    url = reverse('localtv_admin_users')

    def test_GET(self):
        """
        A GET request to the users view should render the
        'localtv/subsite/admin/users.html' template and include a formset for
        the users, an add_user_form, and the headers for the formset.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/users.html')
        self.assertTrue('formset' in response.context[0])
        self.assertTrue('add_user_form' in response.context[0])
        self.assertTrue('headers' in response.context[0])

    def test_POST_add_failure(self):
        """
        A POST to the users view with a POST['submit'] value of 'Add' but a
        failing form should rerender the template.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url,
                          {'submit': 'Add'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/users.html')
        self.assertTrue('formset' in response.context[0])
        self.assertTrue(
            getattr(response.context[0]['add_user_form'],
                    'errors') is not None)
        self.assertTrue('headers' in response.context[0])

    def test_POST_save_failure(self):
        """
        A POST to the users view with a POST['submit'] value of 'Save' but a
        failing formset should rerender the template.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/subsite/admin/users.html')
        self.assertTrue(
            getattr(response.context[0]['formset'], 'errors') is not None)
        self.assertTrue('add_user_form' in response.context[0])
        self.assertTrue('headers' in response.context[0])

    def test_POST_add_no_password(self):
        """
        A POST to the users view with a POST['submit'] of 'Add' and a
        successful form should create a new user and redirect the user back to
        the management page.  If the password isn't specified,
        User.has_unusable_password() should be True.
        """
        c = Client()
        c.login(username="admin", password="admin")
        POST_data = {
            'submit': 'Add',
            'username': 'new',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@testserver.local',
            'role': 'user',
            'description': 'A New User',
            'logo': file(self._data_file('logo.png'))
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        new = User.objects.order_by('-id')[0]
        profile = new.get_profile()
        for key, value in POST_data.items():
            if key == 'submit':
                pass
            elif key == 'role':
                new_site_location = models.SiteLocation.objects.get()
                self.assertFalse(new_site_location.user_is_admin(new))
            elif key == 'logo':
                profile.logo.open()
                value.seek(0)
                self.assertEquals(profile.logo.read(), value.read())
            elif key == 'description':
                self.assertEquals(profile.description, value)
            else:
                self.assertEquals(getattr(new, key), value)

        self.assertFalse(new.has_usable_password())

    def test_POST_add_password(self):
        """
        A POST to the users view with a POST['submit'] of 'Add' and a
        successful form should create a new user and redirect the user back to
        the management page.  If the password is specified, it should be set
        for the user.
        """
        c = Client()
        c.login(username="admin", password="admin")
        POST_data = {
            'submit': 'Add',
            'username': 'new',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@testserver.local',
            'role': 'admin',
            'description': 'A New User',
            'logo': file(self._data_file('logo.png')),
            'password_f': 'new_password',
            'password_f2': 'new_password'
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        new = User.objects.order_by('-id')[0]
        profile = new.get_profile()
        for key, value in POST_data.items():
            if key in ('submit', 'password_f', 'password_f2'):
                pass
            elif key == 'role':
                new_site_location = models.SiteLocation.objects.get()
                self.assertTrue(new_site_location.user_is_admin(new))
            elif key == 'logo':
                profile.logo.open()
                value.seek(0)
                self.assertEquals(profile.logo.read(), value.read())
            elif key == 'description':
                self.assertEquals(profile.description, value)
            else:
                self.assertEquals(getattr(new, key), value)

        self.assertTrue(new.check_password(POST_data['password_f']))

    def test_POST_save_no_changes(self):
        """
        A POST to the users view with a POST['submit'] of 'Save' and a
        successful formset should update the users data.  The default values of
        the formset should not change the values of any of the Users.
        """
        c = Client()
        c.login(username="admin", password="admin")

        user = User.objects.get(username='user')
        # set some profile data, to make sure we're not erasing it
        models.Profile.objects.create(
            user=user,
            logo=File(file(self._data_file('logo.png'))),
            description='Some description about the user')

        old_users = User.objects.values()
        old_profiles = models.Profile.objects.values()

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']

        POST_response = c.post(self.url, self._POST_data_from_formset(
                formset,
                submit='Save'))
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        for old, new in zip(old_users, User.objects.values()):
            self.assertEquals(old, new)
        for old, new in zip(old_profiles, models.Profile.objects.values()):
            self.assertEquals(old, new)

    def test_POST_save_changes(self):
        """
        A POST to the users view with a POST['submit'] of 'Save' and a
        successful formset should update the users data.
        """
        c = Client()
        c.login(username="admin", password="admin")

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']
        POST_data = self._POST_data_from_formset(formset,
                                                 submit='Save')

        # form-0 is admin (3)
        # form-1 is superuser (2)
        # form-2 is user (1)
        POST_data['form-0-first_name'] = 'New First'
        POST_data['form-0-last_name'] = 'New Last'
        POST_data['form-0-role'] = 'user'
        POST_data['form-1-logo'] = file(self._data_file('logo.png'))
        POST_data['form-1-description'] = 'Superuser Description'
        POST_data['form-2-username'] = 'new_admin'
        POST_data['form-2-role'] = 'admin'
        POST_data['form-2-password_f'] = 'new_admin'
        POST_data['form-2-password_f2'] = 'new_admin'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        self.assertEquals(User.objects.count(), 3) # no one got added

        new_admin = User.objects.get(username='new_admin')
        self.assertEquals(new_admin.pk, 1)
        self.assertTrue(self.site_location.user_is_admin(new_admin))
        self.assertTrue(new_admin.check_password('new_admin'))

        superuser = User.objects.get(username='superuser')
        self.assertEquals(superuser.pk, 2)
        self.assertEquals(superuser.is_superuser, True)
        self.assertFalse(superuser in self.site_location.admins.all())
        profile = superuser.get_profile()
        self.assertTrue(profile.logo.name.endswith('logo.png'))
        self.assertEquals(profile.description, 'Superuser Description')

        old_admin = User.objects.get(username='admin')
        self.assertEquals(old_admin.pk, 3)
        self.assertEquals(old_admin.first_name, 'New First')
        self.assertEquals(old_admin.last_name, 'New Last')
        self.assertFalse(self.site_location.user_is_admin(old_admin))

    def test_POST_delete(self):
        """
        A POST to the users view with a POST['submit'] of 'Save' and a
        successful formset should update the users data.  If form-*-DELETE is
        present, that user should be removed, unless that user is a superuser.
        """
        c = Client()
        c.login(username="admin", password="admin")

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']
        POST_data = self._POST_data_from_formset(formset,
                                                 submit='Save')

        # form-0 is admin (3)
        # form-1 is superuser (2)
        # form-2 is user (1)
        POST_data['form-1-DELETE'] = 'yes'
        POST_data['form-2-DELETE'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        self.assertEquals(User.objects.count(), 2) # one user got removed

        self.assertEquals(User.objects.filter(username='user').count(), 0)
        self.assertEquals(User.objects.filter(is_superuser=True).count(), 1)
