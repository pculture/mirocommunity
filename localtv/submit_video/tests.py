from urllib import urlencode

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.client import Client

from localtv import models
from localtv.tests import BaseTestCase

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

    def test_GET(self):
        """
        When the view is accessed via GET, it should render the
        self.template_name template, and get passed a form variable
        via the context.
        XXX The 'scraped_form' form should contain the name,
        description, thumbnail, tags, and URL from the scraped video.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.get(self.url, self.GET_data)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          self.template_name)
        self.assertTrue('form' in response.context[0])

        submit_form = response.context['form']
        self.assertEquals(submit_form.initial['url'], self.POST_data['url'])
        return response

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
        self.assertEquals(response.template[0].name,
                          self.template_name)
        self.assertTrue('form' in response.context[0])
        self.assertTrue(
            getattr(response.context['form'], 'errors') is not None)

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
        self.assertEquals(video.name, self.video_data['name'])
        self.assertEquals(video.description, self.video_data['description'])
        self.assertEquals(video.thumbnail_url, self.video_data['thumbnail'])
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
        'localtv/submit_video/submit.html' template, and get passed a
        'submit_form' in the context.
        """
        c = Client()
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/submit_video/submit.html')
        self.assert_('submit_form' in response.context[0])

    def test_GET_thanks(self):
        """
        A GET request to the thanks view should render the
        'localtv/submit_video/thanks.html' template.
        """
        c = Client()
        response = c.get(reverse('localtv_submit_thanks'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/submit_video/thanks.html')

    def test_GET_thanks_admin(self):
        """
        A GET request to the thanks view from an admin should include their
        last video in the template.
        """
        user = User.objects.get(username='admin')

        models.Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=models.VIDEO_STATUS_ACTIVE,
            website_url='http://www.pculture.org/',
            user=user)

        video2 = models.Video.objects.create(
            site=self.site_location.site,
            name='Get Miro',
            status=models.VIDEO_STATUS_ACTIVE,
            website_url='http://www.getmiro.com/',
            user=user)

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_submit_thanks'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/submit_video/thanks.html')
        self.assertEquals(response.context['video'], video2)

    def test_POST_fail_invalid_form(self):
        """
        If submitting the form fails, the template should be re-rendered with
        the form errors present.
        """
        c = Client()
        response = c.post(self.url,
                          {'url': 'not a URL'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/submit_video/submit.html')
        self.assertTrue('submit_form' in response.context[0])
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
        self.assertEquals(response.template[0].name,
                          'localtv/submit_video/submit.html')
        self.assertTrue('submit_form' in response.context[0])
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
        self.assertEquals(response.template[0].name,
                          'localtv/submit_video/submit.html')
        self.assertTrue('submit_form' in response.context[0])
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
        should be redirected to the scraped_submit_video view.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, {
                'url': 'http://blip.tv/file/10'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          "http://%s%s?%s" %(
                self.site_location.site.domain,
                reverse('localtv_submit_scraped_video'),
                urlencode({
                        'url': 'http://blip.tv/file/10'
                        })))

    def test_POST_succeed_directlink(self):
        """
        If the URL represents a video file, the user should be redirected to
        the directlink_submit_video.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, {
                'url': ('http://blip.tv/file/get/'
                        'Miropcf-Miro20Introduction119.mp4')})
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          "http://%s%s?%s" %(
                self.site_location.site.domain,
                reverse('localtv_submit_directlink_video'),
                urlencode({'url': ('http://blip.tv/file/get/'
                                   'Miropcf-Miro20Introduction119.mp4'),
                           })))

    def test_POST_succeed_embedrequest(self):
        """
        If the URL isn't something we understand normally, the user should be
        redirected to the embedrequest_submit_video view and include the tags.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, {
                'url': 'http://pculture.org/'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          "http://%s%s?%s" %(
                self.site_location.site.domain,
                reverse('localtv_submit_embedrequest_video'),
                urlencode({'url': 'http://pculture.org/'})))

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
                'url': youtube_url + '&feature=player_embedded'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          "http://%s%s?%s" %(
                self.site_location.site.domain,
                reverse('localtv_submit_scraped_video'),
                urlencode({'url': youtube_url})))


class ScrapedTestCase(SecondStepSubmitBaseTestCase):

    def setUp(self):
        SecondStepSubmitBaseTestCase.setUp(self)
        self.url = reverse('localtv_submit_scraped_video')
        self.template_name = 'localtv/submit_video/scraped.html'
        self.video_data = {
            'name': 'Fixing Otter',
            'description': """<span><br />

 In my first produced vlog, I talk a bit about breaking blip.tv, and fixing\
 it.  The audio's pretty bad, sorry about that.<br /></span>""",
            'thumbnail': 'http://a.images.blip.tv/'
                          '11156136631.95334664852457-424.jpg'
            }
        self.POST_data = {
            'url': 'http://blip.tv/file/10',
            'tags': 'tag1, tag2'
            }
        self.GET_data = {
            'url': self.POST_data['url'],
            }

    def test_GET(self):
        """
        In addition to the SecondStepSubmitBaseTestCase.test_GET() assertions,
        the context should have the scraped data.
        """
        response = SecondStepSubmitBaseTestCase.test_GET(self)
        data = response.context[0]['data']
        self.assertEquals(data['title'], self.video_data['name'])
        self.assertEquals(data['description'], """<span><br>

 In my first produced vlog, I talk a bit about breaking blip.tv, and fixing\
 it.  The audio's pretty bad, sorry about that.<br></span>""")
        self.assertEquals(data['thumbnail_url'],
                          self.video_data['thumbnail'])

    def test_POST_fail(self):
        """
        There's no way for this POST to fail in the way this test case tests,
        so we skip it.
        """
        pass

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
                          '11156136631.95334664852457.mp4')
        self.assertEquals(video.embed_code,
                          '<embed src="http://blip.tv/play/g_5Qgm8C" '
                          'type="application/x-shockwave-flash" '
                          'width="480" height="390" '
                          'allowscriptaccess="always" allowfullscreen="true">'
                          '</embed>')

        self.assertEquals(video.authors.count(), 1)
        author = video.authors.all()[0]
        self.assertEquals(author.username, 'mhudack')
        self.assertFalse(author.has_usable_password())
        self.assertEquals(author.get_profile().website,
                          'http://blog.blip.tv/')


class DirectLinkTestCase(SecondStepSubmitBaseTestCase):

    def setUp(self):
        SecondStepSubmitBaseTestCase.setUp(self)
        self.url = reverse('localtv_submit_directlink_video')
        self.template_name = 'localtv/submit_video/direct.html'
        self.POST_data = self.video_data = {
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
        self.template_name = 'localtv/submit_video/embed.html'
        self.POST_data = self.video_data = {
            'url': 'http://www.getmiro.com/',
            'name': 'name',
            'description': 'description',
            'thumbnail': 'http://www.getmiro.com/favicon.ico',
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
        self.assertEquals(video.website_url, self.video_data['url'])
        self.assertEquals(video.file_url, '')
        self.assertEquals(video.embed_code, self.video_data['embed'])

