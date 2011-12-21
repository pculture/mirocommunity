# This file is part of Miro Community.
# Copyright (C) 2009, 2010 Participatory Culture Foundation
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
from urllib import urlencode

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core import mail
from django.template import Context, loader
from django.test.client import Client

from localtv import models
from localtv.submit_video.management.commands import review_status_email
from localtv.tests import BaseTestCase

from notification import models as notification

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
        self.assertEqual(response.template[0].name,
                          self.template_name)
        self.assertTrue('form' in response.context[0])

        form = response.context['form']
        self.assertEqual(form.initial['url'], self.POST_data['url'])
        return response

    def test_GET_fail(self):
        """
        If the URL isn't present in the GET request, the view should redirect
        back to the localtv_submit_video view.
        """
        c = Client()
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_video')))

    def test_GET_existing(self):
        """
        If the URL represents an existing video, the user should be redirected
        to the thanks page.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        video = models.Video.objects.create(site=self.site_location.site,
                                            name='test video',
                                            website_url = self.GET_data['url'])
        c = Client()
        response = c.get(self.url, self.GET_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))
        self.assertEqual(models.Video.objects.filter(
                site=self.site_location.site,
                website_url = self.GET_data['url']).count(), 1)

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
        self.assertEqual(response.template[0].name,
                          self.template_name)
        self.assertTrue('form' in response.context[0])
        self.assertTrue(
            getattr(response.context['form'], 'errors') is not None)

    def test_POST_existing(self):
        """
        If the URL represents an existing video, the user should be redirected
        to the thanks page.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        video = models.Video.objects.create(site=self.site_location.site,
                                            name='test video',
                                            website_url = self.GET_data['url'])
        c = Client()
        response = c.post(self.url, self.GET_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))
        self.assertEqual(models.Video.objects.filter(
                site=self.site_location.site,
                website_url = self.GET_data['url']).count(), 1)

    def test_POST_existing_rejected(self):
        """
        If the URL represents an existing but rejected video, the rejected
        video should be deleted to allow a resubmission..
        """
        video = models.Video.objects.create(
            site=self.site_location.site,
            status=models.Video.REJECTED,
            name='test video',
            website_url = self.GET_data['url'])
        c = Client()
        response = c.post(self.url, self.POST_data)
        video = models.Video.objects.get()
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))

        self.assertEqual(video.status, models.Video.UNAPPROVED)
        self.assertEqual(video.name, self.video_data['name'])
        self.assertEqual(video.description, self.video_data['description'])
        self.assertEqual(video.thumbnail_url, self.video_data['thumbnail'])
        self.assertEqual(set(video.tags.values_list('name', flat=True)),
                          set(('tag1', 'tag2')))
        self.assertEqual(video.contact, 'Foo <bar@example.com>')
        self.assertEqual(len(mail.outbox), 0)

    def test_POST_succeed(self):
        """
        If the POST to the view succeeds, a new Video object should be created
        and the user should be redirected to the localtv_submit_thanks view.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, self.POST_data)
        video = models.Video.objects.all()[0]

        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))

        self.assertEqual(video.status, models.Video.UNAPPROVED)
        self.assertEqual(video.name, self.video_data['name'])
        self.assertEqual(video.description, self.video_data['description'])
        self.assertEqual(video.thumbnail_url, self.video_data['thumbnail'])
        self.assertEqual(set(video.tags.values_list('name', flat=True)),
                          set(('tag1', 'tag2')))
        self.assertEqual(video.contact, 'Foo <bar@example.com>')
        self.assertEqual(video.notes, "here's a note!")
        self.assertEqual(len(mail.outbox), 0)
        return video

    def test_POST_succeed_description_no_images(self):
        """
        Images should be stripped from the video's description.
        """
        original_description = self.video_data['description']
        self.video_data['description'] = original_description + "\
<img src='http://www.google.com/' alt='this should be stripped' />"
        c = Client()
        c.post(self.url, self.POST_data)
        video = models.Video.objects.all()[0]

        self.assertEqual(video.description, original_description)

    def test_POST_succeed_thumbnail_file(self):
        """
        If the user uploads a thumbnail, we should use that and not the
        thumbnail URL.
        """
        c = Client()
        POST_data = self.POST_data.copy()
        POST_data['thumbnail_file'] = file(self._data_file('logo.png'))

        response = c.post(self.url, POST_data)
        video = models.Video.objects.all()[0]

        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))
        self.assertTrue(video.has_thumbnail)
        self.assertEqual(video.thumbnail_url, '')
        self.assertEqual(video.thumbnail_extension, 'png')

    def test_POST_succeed_email(self):
        """
        If the POST to the view succeeds and admins are subscribed to the
        'admin_new_submission' notice, an e-mail should be sent to the site
        admins.
        """
        notice_type = notification.NoticeType.objects.get(
            label='admin_new_submission')
        for username in 'admin', 'superuser':
            user = User.objects.get(username=username)
            setting = notification.get_notification_setting(user, notice_type,
                                                            "1")
            setting.send = True
            setting.save()

        c = Client()
        c.post(self.url, self.POST_data)

        video = models.Video.objects.all()[0]

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        for recipient in message.to:
            u = User.objects.get(email=recipient)
            self.assertTrue(self.site_location.user_is_admin(u))

        self.assertEqual(message.subject,
                          '[%s] New Video in Review Queue: %s' % (
                video.site.name, video))

        t = loader.get_template('localtv/submit_video/new_video_email.txt')
        c = Context({'video': video})
        self.assertEqual(message.body, t.render(c))

    def test_POST_succeed_email_admin(self):
        """
        If the submitting user is an admin, no e-mail should be sent.
        """
        notice_type = notification.NoticeType.objects.get(
            label='admin_new_submission')
        for username in 'admin', 'superuser':
            user = User.objects.get(username=username)
            setting = notification.get_notification_setting(user, notice_type,
                                                            "1")
            setting.send = True
            setting.save()

        c = Client()
        c.login(username='admin', password='admin')
        c.post(self.url, self.POST_data)
        self.assertEqual(len(mail.outbox), 0)

    def test_POST_succeed_admin(self):
        """
        If the POST to the view succeeds and the user is an admin, the video
        should be automatically approved, and the user should be saved along
        with the video.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url, self.POST_data)
        video = models.Video.objects.all()[0]

        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))

        self.assertEqual(video.status, models.Video.ACTIVE)
        self.assertEqual(video.when_approved, video.when_submitted)
        self.assertEqual(video.user, User.objects.get(username='admin'))


class SubmitVideoTestCase(SubmitVideoBaseTestCase):

    def setUp(self):
        SubmitVideoBaseTestCase.setUp(self)
        self.url = reverse('localtv_submit_video')

    def test_GET(self):
        """
        A GET request to the submit video page should render the
        'localtv/submit_video/submit.html' template, and get passed a
        'form' in the context.
        """
        c = Client()
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/submit_video/submit.html')
        self.assertTrue('form' in response.context[0])

    def test_GET_thanks(self):
        """
        A GET request to the thanks view should render the
        'localtv/submit_video/thanks.html' template.  It should not include a
        video in the context, even if one is specified in the URL.
        """
        c = Client()
        response = c.get(reverse('localtv_submit_thanks'))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/submit_video/thanks.html')
        self.assertFalse('video' in response.context[0])

        response = c.get(reverse('localtv_submit_thanks', args=[1]))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/submit_video/thanks.html')
        self.assertFalse('video' in response.context[0])

    def test_GET_thanks_admin(self):
        """
        A GET request to the thanks view from an admin should include the video
        referenced in the URL.
        """
        user = User.objects.get(username='admin')

        video = models.Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=models.Video.ACTIVE,
            website_url='http://www.pculture.org/',
            user=user)

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_submit_thanks',
                                 args=[video.pk]))
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/submit_video/thanks.html')
        self.assertEqual(response.context['video'], video)

    def test_POST_fail_invalid_form(self):
        """
        If submitting the form fails, the template should be re-rendered with
        the form errors present.
        """
        c = Client()
        response = c.post(self.url,
                          {'url': 'not a URL'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/submit_video/submit.html')
        self.assertTrue('form' in response.context[0])
        self.assertTrue(getattr(
                response.context['form'], 'errors') is not None)

    def test_POST_fail_existing_video_approved(self):
        """
        If the URL represents an approved video on the site, the form should be
        rerendered.  A 'was_duplicate' variable bound to True, and a 'video'
        variable bound to the Video object should be added to the context.
        """
        video = models.Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=models.Video.ACTIVE,
            website_url='http://www.pculture.org/')

        c = Client()
        response = c.post(self.url,
                          {'url': video.website_url})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/submit_video/submit.html')
        self.assertTrue('form' in response.context[0])
        self.assertTrue(response.context['was_duplicate'])
        self.assertEqual(response.context['video'], video)

    def test_POST_existing_rejected(self):
        """
        If the URL represents an existing but rejected video, the video should
        be put into the review queue.
        """
        video = models.Video.objects.create(
            site=self.site_location.site,
            status=models.Video.REJECTED,
            name='test video',
            website_url = 'http://www.pculture.org/')

        c = Client()
        response = c.post(self.url,
                          {'url': video.website_url})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          "http://%s%s?%s" %(
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_embedrequest_video'),
                urlencode({'url': video.website_url})))
        self.assertEqual(models.Video.objects.count(), 0)

    def test_POST_fail_existing_video_approved_admin(self):
        """
        If the URL represents the website URL of an approved video on the site
        and the user is an admin, the user should be redirected to the thanks
        page.
        """
        video = models.Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=models.Video.ACTIVE,
            website_url='http://www.pculture.org/')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url,
                          {'url': video.website_url})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))

    def test_POST_fail_existing_video_file_url(self):
        """
        If the URL represents the file URL of an existing video, the form
        should be rerendered.  A 'was_duplicate' variable bound to True, and a
        'video' variable bound to the Video object should be added to the
        context.
        """
        video = models.Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=models.Video.ACTIVE,
            file_url='http://www.pculture.org/')

        c = Client()
        response = c.post(self.url,
                          {'url': video.file_url})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/submit_video/submit.html')
        self.assertTrue('form' in response.context[0])
        self.assertTrue(response.context['was_duplicate'])
        self.assertEqual(response.context['video'], video)

    def test_POST_fail_existing_video_file_url_admin(self):
        """
        If the URL represents the file URL of an approved video on the site and
        the user is an admin, the user should be redirected to the thanks page.
        """
        video = models.Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=models.Video.ACTIVE,
            file_url='http://www.pculture.org/')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url,
                          {'url': video.file_url})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))

    def test_POST_fail_existing_video_unapproved(self):
        """
        If the URL represents an unapproved video on the site, the form should
        be rerendered.  A 'was_duplicate' variable bound to True, and a 'video'
        variable bound to None should be added to the context.
        """
        video = models.Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=models.Video.UNAPPROVED,
            website_url='http://www.pculture.org/')

        c = Client()
        response = c.post(self.url,
                          {'url': video.website_url})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/submit_video/submit.html')
        self.assertTrue('form' in response.context[0])
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
            status=models.Video.UNAPPROVED,
            website_url='http://www.pculture.org/')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url,
                          {'url': video.website_url})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))

        video = models.Video.objects.get(pk=video.pk)
        self.assertEqual(video.status,models.Video.ACTIVE)

    def test_GET_bookmarklet(self):
        """
        A GET request with a 'url' option should also submit the form.
        """
        GET_data = {'url': ('http://media.river-valley.tv/conferences/'
                            'lgm2009/0302-Jean_Francois_Fortin_Tam-ogg.php')}
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.get(self.url, GET_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          "http://%s%s?%s" %(
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_directlink_video'),
                urlencode(GET_data)))

    def test_POST_succeed_scraped(self):
        """
        If the URL represents a site that VidScraper understands, the user
        should be redirected to the scraped_submit_video view.
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, {
                'url': 'http://blip.tv/searching-for-mike/fixing-otter-267'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          "http://%s%s?%s" %(
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_scraped_video'),
                urlencode({
                        'url': ('http://blip.tv/searching-for-mike/'
                                'fixing-otter-267')
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
        self.assertEqual(response['Location'],
                          "http://%s%s?%s" %(
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_directlink_video'),
                urlencode({'url': ('http://blip.tv/file/get/'
                                   'Miropcf-Miro20Introduction119.mp4'),
                           })))

    def test_POST_succeed_directlink_HEAD(self):
        """
        If the URL represents a video file, but doesn't have a standard video
        extension, a HEAD request should be made to figure out that the URL is
        a video file.
        """
        GET_data = {'url': ('http://media.river-valley.tv/conferences/'
                            'lgm2009/0302-Jean_Francois_Fortin_Tam-ogg.php')}
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        c = Client()
        response = c.post(self.url, GET_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          "http://%s%s?%s" %(
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_directlink_video'),
                urlencode(GET_data)))

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
        self.assertEqual(response['Location'],
                          "http://%s%s?%s" %(
                'testserver', #self.site_location.site.domain,
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
        long_url = ('http://www.youtube.com/watch?gl=US&v=AfsZzeNF8A4'
                    '&feature=player_embedded')
        response = c.post(self.url, {'url': long_url})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          "http://%s%s?%s" %(
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_scraped_video'),
                urlencode({'url': youtube_url})))

    def test_POST_succeed_pound(self):
        """
        If the URL has a # in it, it should be stripped but the submission
        should continue normally..
        """
        # TODO(pswartz) this should probably be mocked, instead of actually
        # hitting the network
        url = 'http://www.msnbc.msn.com/id/21134540/vp/35294347'
        c = Client()
        response = c.post(self.url, {'url': url + '#28863649'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          "http://%s%s?%s" %(
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_embedrequest_video'),
                urlencode({'url': url})))

class ScrapedTestCase(SecondStepSubmitBaseTestCase):

    def setUp(self):
        SecondStepSubmitBaseTestCase.setUp(self)
        self.url = reverse('localtv_submit_scraped_video')
        self.template_name = 'localtv/submit_video/scraped.html'
        self.video_data = {
            'name': 'Fixing Otter',
            'description': u"<p>In my first produced vlog, I talk a bit about \
breaking blip.tv, and fixing it. The audio's pretty bad, sorry \
about that.</p>",
            'thumbnail': 'http://a.images.blip.tv/'
                          '11156136631.95334664852457-424.jpg'
            }
        self.POST_data = {
            'url': 'http://blip.tv/searching-for-mike/fixing-otter-267',
            'tags': 'tag1, tag2',
            'contact': 'Foo <bar@example.com>',
            'notes': "here's a note!"
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
        video = response.context[0]['video']
        self.assertEqual(video.title, self.video_data['name'])
        self.assertEqual(video.description,
                          """<p>In my first produced vlog, I talk a bit \
about breaking blip.tv, and fixing it. The audio's pretty bad, sorry about \
that.</p>""")
        self.assertEqual(video.thumbnail_url,
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
        self.assertEqual(video.website_url, self.POST_data['url'])
        self.assertEqual(video.file_url,
                          'http://blip.tv/file/get/'
                          '11156136631.95334664852457.mp4')
        self.assertEqual(video.embed_code,
                          u'<iframe src="http://blip.tv/play/hbF4gm8C.html" \
width="480" height="390" frameborder="0" allowfullscreen></iframe>\
<embed type="application/x-shockwave-flash" \
src="http://a.blip.tv/api.swf#hbF4gm8C" style="display:none"></embed>')
        self.assertEqual(video.file_url_length, 9236973)
        self.assertEqual(video.file_url_mimetype, 'video/mp4')

        self.assertEqual(video.authors.count(), 1)
        author = video.authors.all()[0]
        self.assertEqual(author.username, 'mhudack')
        self.assertFalse(author.has_usable_password())
        self.assertEqual(author.get_profile().website,
                          'http://blog.blip.tv/')

    def test_POST_succeed_thumbnail_file(self):
        """
        We don't have a thumbnail upload for this form, so we skip the test.
        """
        pass


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
            'tags': 'tag1, tag2',
            'contact': 'Foo <bar@example.com>',
            'notes': "here's a note!"
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
        self.assertEqual(video.website_url, self.POST_data['website_url'])
        self.assertEqual(video.file_url, self.POST_data['url'])
        self.assertEqual(video.file_url_length, 9436882)
        self.assertEqual(video.file_url_mimetype, 'video/mp4')
        self.assertEqual(video.embed_code, '')

    def test_POST_succeed_bad_mimetype(self):
        """
        If the URL submitted doesn't give us a good MIME type back, guess a
        better one.
        """
        self.POST_data['url'] = ('http://mpegmedia.abc.net.au/tv/catalyst/'
                                 'catalyst_s12_ep16_DeepSeaMining.mp4')
        video = SecondStepSubmitBaseTestCase.test_POST_succeed(self)
        self.assertEqual(video.file_url_mimetype, 'video/mp4')

    def test_GET_existing_file_url(self):
        """
        If the URL represents an existing file URL, the user should be
        redirected to the thanks page.
        """
        video = models.Video.objects.create(site=self.site_location.site,
                                            name='test video',
                                            file_url = self.GET_data['url'])
        c = Client()
        response = c.get(self.url, self.GET_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))
        self.assertEqual(models.Video.objects.filter(
                site=self.site_location.site,
                file_url = self.GET_data['url']).count(), 1)

    def test_POST_existing_file_url(self):
        """
        If the URL represents an existing file URL, the user should be
        redirected to the thanks page.
        """
        video = models.Video.objects.create(site=self.site_location.site,
                                            name='test video',
                                            file_url = self.GET_data['url'])
        c = Client()
        response = c.post(self.url, self.GET_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver', #self.site_location.site.domain,
                reverse('localtv_submit_thanks',
                        args=[video.pk])))
        self.assertEqual(models.Video.objects.filter(
                site=self.site_location.site,
                file_url = self.GET_data['url']).count(), 1)


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
            'tags': 'tag1, tag2',
            'contact': 'Foo <bar@example.com>',
            'notes': "here's a note!"
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
        self.assertEqual(video.website_url, self.video_data['url'])
        self.assertEqual(video.file_url, '')
        self.assertEqual(video.embed_code, self.video_data['embed'])


class ReviewStatusEmailCommandTestCase(BaseTestCase):

    fixtures = BaseTestCase.fixtures + ['videos']

    def setUp(self):
        BaseTestCase.setUp(self)
        notice_type = notification.NoticeType.objects.get(
            label='admin_queue_daily')
        for username in 'admin', 'superuser':
            user = User.objects.get(username=username)
            setting = notification.get_notification_setting(user, notice_type,
                                                            "1")
            setting.send = True
            setting.save()

    def test_no_email(self):
        """
        If no videos are new in the previous day, no e-mail should be sent.
        """
        review_status_email.Command().handle_noargs()
        self.assertEqual(len(mail.outbox), 0)

    def test_email(self):
        """
        If there is a video submitted in the previous day, an e-mail should be
        sent
        """
        queue_videos = models.Video.objects.filter(
            status=models.Video.UNAPPROVED)

        new_video = queue_videos[0]
        new_video.when_submitted = datetime.datetime.now() - \
            datetime.timedelta(hours=23, minutes=59)
        new_video.save()

        review_status_email.Command().handle_noargs()
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertEqual(message.subject,
                          'Video Submissions for testserver')
        t = loader.get_template('localtv/submit_video/review_status_email.txt')
        c = Context({'queue_videos': queue_videos,
                     'new_videos': queue_videos.filter(pk=new_video.pk),
                     'time_period': 'today',
                     'site': self.site_location.site})
        self.assertEqual(message.body, t.render(c))

    def test_no_email_without_setting(self):
        """
        If no admins are subscribed, no e-mail should be sent.
        """
        notice_type = notification.NoticeType.objects.get(
            label='admin_queue_daily')
        for username in 'admin', 'superuser':
            user = User.objects.get(username=username)
            setting = notification.get_notification_setting(user, notice_type,
                                                            "1")
            setting.send = False
            setting.save()

        queue_videos = models.Video.objects.filter(
            status=models.Video.UNAPPROVED)

        new_video = queue_videos[0]
        new_video.when_submitted = datetime.datetime.now()
        new_video.save()

        review_status_email.Command().handle_noargs()
        self.assertEqual(len(mail.outbox), 0)
