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
from urllib import urlencode, quote_plus

from django.contrib.auth.models import User
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core import mail
from django.forms.fields import URLField
from django.template import Context, loader
from django.test.client import Client

from localtv.models import Video
from localtv.submit_video.forms import SubmitURLForm, SubmitVideoForm
from localtv.submit_video.management.commands import review_status_email
from localtv.submit_video.views import (SubmitURLView, SubmitVideoView,
                                        submit_thanks)
from localtv.tests import BaseTestCase

from notification import models as notification


class SubmitThanksFunctionalTestCase(BaseTestCase):
    fixtures = ['videos'] + BaseTestCase.fixtures

    def setUp(self):
        BaseTestCase.setUp(self)
        self.url = reverse('localtv_submit_thanks')
        self.video = Video.objects.filter(status=Video.ACTIVE)[0]
        self.url_with_video = reverse('localtv_submit_thanks', args=[self.video.pk])
        self.template_name = 'localtv/submit_video/thanks.html'

    def test_get__simple(self):
        """
        A GET request to the thanks view by a normal user is expected to render
        the 'localtv/submit_video/thanks.html' template.  It should not include
        a video in the context, even if one is specified in the URL.

        """
        c = Client()
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name, self.template_name)
        self.assertFalse('video' in response.context[0])

        response = c.get(self.url_with_video)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name, self.template_name)
        self.assertFalse('video' in response.context[0])

    def test_get__admin(self):
        """
        A GET request to the thanks view from an admin should include the video
        referenced in the URL.

        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name, self.template_name)
        self.assertFalse('video' in response.context[0])

        response = c.get(self.url_with_video)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name, self.template_name)
        self.assertTrue('video' in response.context[0])
        self.assertEqual(response.context['video'], self.video)


class SubmitVideoBaseFunctionalTestCase(BaseTestCase):
    """
    Functional test case of permissions.

    """
    abstract = True

    def assertLoginRedirect(self, url, username=None, password=None):
        """
        Asserts that a user logged in with the given credentials will be
        redirected to the login view from the given url.

        """
        c = Client()

        if username is not None and password is not None:
            c.login(username=username, password=password)

        response = c.get(url)
        self.assertRedirects(response, "%s?next=%s" % (settings.LOGIN_URL,
                                                    quote_plus(url, safe='/')))

    def assertNoLoginRedirect(self, url, username=None, password=None):
        """
        Asserts that a user logged in with the given credentials will not be
        redirected to the login view from the given url.

        """
        c = Client()

        if username is not None and password is not None:
            c.login(username=username, password=password)

        response = c.get(url)
        self.assertFalse(response.status_code == 302 and 
                         response['Location'] == (
                         'http://%s%s?next=%s' %
                         ('testserver',
                          settings.LOGIN_URL,
                          quote_plus(url, safe='/'))))

    def test_all_permitted(self):
        """
        If login is not required, all requests should pass the permissions
        check.

        """
        self.site_location.submission_requires_login = False
        self.site_location.save()

        self.assertNoLoginRedirect(self.url)
        self.assertNoLoginRedirect(self.url, username='user',
                                   password='password')
        self.assertNoLoginRedirect(self.url, username='admin', password='admin')

    def test_login_required(self):
        """
        If login is required and a submit button is available, all logged-in
        requests should pass the permissions check.

        """
        self.site_location.submission_requires_login = True
        self.site_location.display_submit_button = True
        self.site_location.save()

        self.assertLoginRedirect(self.url)
        self.assertNoLoginRedirect(self.url, username='user',
                                   password='password')
        self.assertNoLoginRedirect(self.url, username='admin', password='admin')

    def test_admin_required(self):
        """
        If login is required and no submit button is displayed, only admin
        requests should pass the permissions check.

        """
        self.site_location.submission_requires_login = True
        self.site_location.display_submit_button = False
        self.site_location.save()

        self.assertLoginRedirect(self.url)
        self.assertLoginRedirect(self.url, username='user', password='password')
        self.assertNoLoginRedirect(self.url, username='admin', password='admin')


class SubmitURLFunctionalTestCase(SubmitVideoBaseFunctionalTestCase):
    def setUp(self):
        SubmitVideoBaseFunctionalTestCase.setUp(self)
        self.url = reverse('localtv_submit_video')
        self.template_name = 'localtv/submit_video/submit.html'

    def test_get__simple(self):
        """
        A GET request to the SubmitURLView without any GET data is expected to
        render the 'localtv/submit_video/submit.html' template, and get passed a
        'form' in the context which is an instance of SubmitURLForm. The same
        should be true if GET parameters are supplied which do not overlap with
        the form fields.

        """
        c = Client()
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context[0])
        self.assertIsInstance(response.context[0]['form'], SubmitURLForm)
        self.assertFalse(response.context['form'].is_bound)

        response = c.get(self.url, {'q': 'hello', 'next': '/blink/'})
        self.assertStatusCodeEquals(response, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context[0])
        self.assertIsInstance(response.context[0]['form'], SubmitURLForm)
        self.assertFalse(response.context['form'].is_bound)

    def test_submit__succeed(self):
        """
        A GET request to the SubmitURLView with GET data should submit the form
        if the GET data overlaps with the form field(s). On success, the user
        should be redirected to the correct submission completion view,
        preserving GET data.

        All the views to which the user could be redirected are instances of the
        same class-based view. This is essentially a test for
        backwards-compatibility.

        """
        # TODO: If there is a way to mock these requests, that would be great.
        data = {'url': ('http://blip.tv/file/get/'
                        'Miropcf-Miro20Introduction119.mp4'),
                'q': 'hello',
                'next': 'blink'}
        c = Client()

        # Case one: Direct link to a video file.
        expected_url = "%s?%s" % (
            reverse('localtv_submit_directlink_video'),
            urlencode(data)
        )
        response = c.get(self.url, data)
        self.assertRedirects(response, expected_url)

        # Case two: Link to a page that vidscraper can scrape.
        data['url'] = 'http://blip.tv/searching-for-mike/fixing-otter-267'
        expected_url = "%s?%s" % (
            reverse('localtv_submit_scraped_video'),
            urlencode(data)
        )
        response = c.get(self.url, data)
        self.assertRedirects(response, expected_url)

        # Case three: Link to a page that vidscraper doesn't understand.
        data['url'] = 'http://pculture.org/'
        expected_url = "%s?%s" % (
            reverse('localtv_submit_embedrequest_video'),
            urlencode(data)
        )
        response = c.get(self.url, data)
        self.assertRedirects(response, expected_url)

    def test_submit__unusual_extension(self):
        """
        If a URL represents a video file, but has an unusual extension, localtv
        should figure out what's going on.

        """
        data = {'url': ('http://media.river-valley.tv/conferences/'
                            'lgm2009/0302-Jean_Francois_Fortin_Tam-ogg.php')}
        
        expected_url = "%s?%s" % (
            reverse('localtv_submit_directlink_video'),
            urlencode(data)
        )
        c = Client()

        response = c.get(self.url, data)
        self.assertRedirects(response, expected_url)

    def test_submit__existing_rejected(self):
        """
        If the URL represents an existing but rejected video, the user should be
        redirected to the correct submission view, but the existing video should
        not yet be deleted.

        """
        video = Video.objects.create(
            site=self.site_location.site,
            status=Video.REJECTED,
            name='test video',
            website_url = 'http://www.pculture.org/')
        expected_url = "%s?%s" % (
            reverse('localtv_submit_embedrequest_video'),
            urlencode({'url': video.website_url})
        )

        c = Client()
        response = c.get(self.url, {'url': video.website_url})
        self.assertRedirects(response, expected_url)
        self.assertEqual(list(Video.objects.filter(pk=video.pk)), [video])

    def test_submit__existing_unapproved(self):
        """
        If the URL represents an existing but unmoderated video, the form should
        be redisplayed. Additionally, the context should contain two variables
        for backwards-compatibility:

            * ``was_duplicate``: True
            * ``video``: The duplicate video instance
        
        """
        expected_error = "That video has already been submitted!"
        video = Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=Video.UNAPPROVED,
            website_url='http://www.pculture.org/')

        c = Client()
        response = c.get(self.url,
                          {'url': video.website_url})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFormError(response, 'form', 'url', [expected_error])
        self.assertTrue(response.context['was_duplicate'])
        self.assertTrue(response.context['video'] is None)

    def test_submit__existing_approved(self):
        """
        If the URL represents an existing and approved video, the form should be
        redisplayed. Additionally, the context should contain two variables for
        backwards-compatibility:

            * ``was_duplicate``: True
            * ``video``: The duplicate video instance

        """
        url = 'http://www.pculture.org/'
        video = Video.objects.create(
            site=self.site_location.site,
            name='Participatory Culture',
            status=Video.ACTIVE,
            file_url=url
        )
        expected_error = "That video has already been submitted!"
        c = Client()

        # Case one: duplicate file url
        response = c.get(self.url, {'url': url})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFormError(response, 'form', 'url', [expected_error])
        self.assertTrue(response.context['was_duplicate'])
        self.assertEqual(response.context['video'], video)

        # Case two: duplicate website url
        video.website_url = url
        video.file_url = ''
        video.save()

        response = c.get(self.url, {'url': url})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFormError(response, 'form', 'url', [expected_error])
        self.assertTrue(response.context['was_duplicate'])
        self.assertEqual(response.context['video'], video)

        # Case three: duplicate guid. TODO: It would be preferable to mock this.
        # TODO: vidscraper currently is changing the guids on youtube videos.
        # Once that is resolved one way or another, this will need to be tweaked
        # accordingly.
        #video.guid = 'tag:youtube.com,2008:video:J_DV9b0x7v4'
        video.guid = u'http://gdata.youtube.com/feeds/api/videos/J_DV9b0x7v4'
        video.save()

        response = c.get(self.url, {'url': 'http://www.youtube.com/watch?v=J_DV9b0x7v4'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFormError(response, 'form', 'url', [expected_error])
        self.assertTrue(response.context['was_duplicate'])
        self.assertEqual(response.context['video'], video)

    def test_submit__invalid_input(self):
        """
        Tests that the form will be redisplayed if invalid.

        """
        expected_error = URLField.default_error_messages['invalid']
        c = Client()
        response = c.get(self.url, {'url': 'invalid URL'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFormError(response, 'form', 'url', [expected_error])


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
        queue_videos = Video.objects.filter(
            status=Video.UNAPPROVED)

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

        queue_videos = Video.objects.filter(
            status=Video.UNAPPROVED)

        new_video = queue_videos[0]
        new_video.when_submitted = datetime.datetime.now()
        new_video.save()

        review_status_email.Command().handle_noargs()
        self.assertEqual(len(mail.outbox), 0)
