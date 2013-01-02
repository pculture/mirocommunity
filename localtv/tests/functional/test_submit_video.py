import datetime
from urllib import urlencode, quote_plus

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse, reverse_lazy
from django.core import mail
from django.forms.fields import URLField
from django.template import Context, loader
from django.test import Client
from notification import models as notification
from mock import patch
import vidscraper
from vidscraper.videos import Video as VidscraperVideo

from localtv.models import Video, SiteSettings
from localtv.submit_video import forms
from localtv.submit_video.management.commands import review_status_email
from localtv.submit_video.views import SubmitURLView
from localtv.tasks import video_save_thumbnail
from localtv.tests import BaseTestCase


class SubmitThanks(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.url = reverse('localtv_submit_thanks')
        self.create_user('admin', 'admin', is_superuser=True)
        self.video = self.create_video(update_index=False)
        self.url_with_video = reverse('localtv_submit_thanks', args=[
                self.video.pk])
        self.template_name = 'localtv/submit_video/thanks.html'

    def test_get__simple(self):
        """
        A GET request to the thanks view by a normal user is expected to render
        the 'localtv/submit_video/thanks.html' template.  It should not include
        a video in the context, even if one is specified in the URL.

        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, self.template_name)
        self.assertFalse('video' in response.context[0])

        response = self.client.get(self.url_with_video)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, self.template_name)
        self.assertFalse('video' in response.context[0])

    def test_get__admin(self):
        """
        A GET request to the thanks view from an admin should include the video
        referenced in the URL.

        """
        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, self.template_name)
        self.assertFalse('video' in response.context[0])

        response = self.client.get(self.url_with_video)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, self.template_name)
        self.assertTrue('video' in response.context[0])
        self.assertEqual(response.context['video'], self.video)


class Permissions(BaseTestCase):
    """
    Functional test case of permissions.

    """
    def setUp(self):
        BaseTestCase.setUp(self)
        self.site_settings = SiteSettings.objects.get_current()
        self.create_user('user', 'password')
        self.create_user('admin', 'admin', is_superuser=True)

    def assertHasAuthentication(self, url, username=None, password=None):
        """
        Asserts that a user logged in with the given credentials will not be
        redirected to the login view from the given url.

        """
        c = Client()

        if username is not None and password is not None:
            c.login(username=username, password=password)

        response = c.get(url)
        login_url = "http://testserver{path}?next={next}".format(
                        path=settings.LOGIN_URL, next=quote_plus(url, safe='/'))
        self.assertFalse(response.status_code == 302 and
                         response['Location'] == login_url)

    def _test_all_permitted(self, url):
        """
        If login is not required, all requests should pass the permissions
        check.

        """
        self.site_settings.submission_requires_login = False
        self.site_settings.save()

        self.assertHasAuthentication(url)
        self.assertHasAuthentication(url,
                                     username='user',
                                     password='password')
        self.assertHasAuthentication(url,
                                     username='admin',
                                     password='admin')

    def test_all_permitted__submit(self):
        self._test_all_permitted(reverse('localtv_submit_video'))

    def test_all_permitted__scraped(self):
        self._test_all_permitted(reverse('localtv_submit_scraped_video'))

    def test_all_permitted__embed(self):
        self._test_all_permitted(reverse('localtv_submit_embedrequest_video'))

    def test_all_permitted__directlink(self):
        self._test_all_permitted(reverse('localtv_submit_directlink_video'))

    def _test_login_required(self, url):
        """
        If login is required and a submit button is available, all logged-in
        requests should pass the permissions check.

        """
        self.site_settings.submission_requires_login = True
        self.site_settings.display_submit_button = True
        self.site_settings.save()

        self.assertRequiresAuthentication(url)
        self.assertHasAuthentication(url,
                                     username='user',
                                     password='password')
        self.assertHasAuthentication(url,
                                     username='admin',
                                     password='admin')

    def test_login_required__submit(self):
        self._test_login_required(reverse('localtv_submit_video'))

    def test_login_required__scraped(self):
        self._test_login_required(reverse('localtv_submit_scraped_video'))

    def test_login_required__embed(self):
        self._test_login_required(reverse('localtv_submit_embedrequest_video'))

    def test_login_required__directlink(self):
        self._test_login_required(reverse('localtv_submit_directlink_video'))

    def _test_admin_required(self, url):
        """
        If login is required and no submit button is displayed, only admin
        requests should pass the permissions check.

        """
        self.site_settings.submission_requires_login = True
        self.site_settings.display_submit_button = False
        self.site_settings.save()

        self.assertRequiresAuthentication(url)
        self.assertRequiresAuthentication(url,
                                          username='user',
                                          password='password')
        self.assertHasAuthentication(url,
                                     username='admin',
                                     password='admin')

    def test_admin_required__submit(self):
        self._test_admin_required(reverse('localtv_submit_video'))

    def test_admin_required__scraped(self):
        self._test_admin_required(reverse('localtv_submit_scraped_video'))

    def test_admin_required__embed(self):
        self._test_admin_required(reverse('localtv_submit_embedrequest_video'))

    def test_admin_required__directlink(self):
        self._test_admin_required(reverse('localtv_submit_directlink_video'))


class SubmitURLViewTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.site_settings = SiteSettings.objects.get_current()
        self.url = reverse('localtv_submit_video')
        self.template_name = 'localtv/submit_video/submit.html'

    def test_get(self):
        """
        A GET request to the SubmitURLView without any GET data is expected to
        render the 'localtv/submit_video/submit.html' template, and get passed
        a 'form' in the context which is an instance of SubmitURLForm. The same
        should be true if GET parameters are supplied which do not overlap with
        the form fields.

        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context[0])
        self.assertIsInstance(response.context['form'], forms.SubmitURLForm)
        self.assertFalse(response.context['form'].is_bound)

        response = self.client.get(self.url, {'q': 'hello', 'next': '/blink/'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context[0])
        self.assertIsInstance(response.context['form'], forms.SubmitURLForm)
        self.assertFalse(response.context['form'].is_bound)

    def _test_submit__succeed(self, url, next_view, **kwargs):
        """
        A GET request to the SubmitURLView with GET data should submit the form
        if the GET data overlaps with the form field(s). On success, the user
        should be redirected to the correct submission completion view,
        preserving GET data.

        All the views to which the user could be redirected are instances of
        the same class-based view. This is essentially a test for
        backwards-compatibility.

        """
        data = {'url': url,
                'q': 'hello',
                'next': 'blink'}
        expected_url = "%s?%s" % (
            reverse(next_view),
            urlencode(data)
        )
        video = VidscraperVideo(url)
        video._loaded = True
        for attr, value in kwargs.iteritems():
            setattr(video, attr, value)
        with patch.object(vidscraper, 'auto_scrape', return_value=video):
            response = self.client.get(self.url, data)
        self.assertRedirects(response, expected_url)

    def test_submit__succeed__scraped(self):
        self._test_submit__succeed('http://blip.tv/searching-for-mike/fixing-otter-267',
                                   'localtv_submit_scraped_video',
                                   embed_code='haha')

    def test_submit__succeed__directlink(self):
        self._test_submit__succeed('http://blip.tv/file/get/Miropcf-Miro20Introduction119.mp4',
                                   'localtv_submit_directlink_video')

    def test_submit__succeed__embedrequest(self):
        self._test_submit__succeed('http://pculture.org/',
                                   'localtv_submit_embedrequest_video')

    def test_submit__succeed__unusual_extension(self):
        """
        If a URL represents a video file, but has an unusual extension, localtv
        should figure out what's going on.

        """
        with patch('localtv.submit_video.views.is_video_url', lambda x: True):
            self._test_submit__succeed('http://media.river-valley.tv/conferences/lgm2009/0302-Jean_Francois_Fortin_Tam-ogg.php',
                                       'localtv_submit_directlink_video')

    def test_submit__existing_rejected(self):
        """
        If the URL represents an existing but rejected video, the user should
        be redirected to the correct submission view, but the existing video
        should not yet be deleted.

        """
        url = 'http://www.pculture.org/'
        video = Video.objects.create(site=self.site_settings.site,
                                     status=Video.REJECTED,
                                     name='test video',
                                     website_url=url)
        self._test_submit__succeed(url,
                                   'localtv_submit_embedrequest_video')
        self.assertEqual(list(Video.objects.filter(pk=video.pk)), [video])

    def test_submit__existing_unapproved(self):
        """
        If the URL represents an existing but unmoderated video, the form
        should be redisplayed. Additionally, the context should contain two
        variables for backwards-compatibility:

            * ``was_duplicate``: ``True``
            * ``video``: ``None``

        """
        expected_error = "That video has already been submitted!"
        video = Video.objects.create(
            site=self.site_settings.site,
            name='Participatory Culture',
            status=Video.UNAPPROVED,
            website_url='http://www.pculture.org/')

        response = self.client.get(self.url,
                          {'url': video.website_url})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFormError(response, 'form', 'url', [expected_error])
        self.assertTrue(response.context['was_duplicate'])
        self.assertTrue(response.context['video'] is None)

    def _test_submit__existing_approved(self, video_kwargs=None, vidscraper_kwargs=None):
        """
        If the URL represents an existing and approved video, the form should
        be redisplayed. Additionally, the context should contain two variables
        for backwards-compatibility:

            * ``was_duplicate``: True
            * ``video``: The duplicate video instance

        """
        video = Video.objects.create(
            site=self.site_settings.site,
            name='Participatory Culture',
            status=Video.ACTIVE,
            **video_kwargs
        )
        data = {'url': 'http://pculture.org/'}
        expected_error = "That video has already been submitted!"

        vidscraper_video = VidscraperVideo(data['url'])
        for attr, value in (vidscraper_kwargs or {}).iteritems():
            setattr(vidscraper_video, attr, value)
        with patch.object(vidscraper, 'auto_scrape', return_value=vidscraper_video):
            response = self.client.get(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFormError(response, 'form', 'url', [expected_error])
        self.assertTrue(response.context['was_duplicate'])
        self.assertEqual(response.context['video'], video)

    def test_submit__existing_approved__file_url(self):
        data = {'file_url': 'http://pculture.org/'}
        self._test_submit__existing_approved(data, data)

    def test_submit__existing_approved__website_url(self):
        url = 'http://pculture.org/'
        self._test_submit__existing_approved({'website_url': url},
                                             {'link': url})

    def test_submit__existing_approved__guid(self):
        data = {'guid': u'http://gdata.youtube.com/feeds/api/videos/J_DV9b0x7v4'}
        self._test_submit__existing_approved(data, data)

    def test_submit__invalid_input(self):
        """
        Tests that the form will be redisplayed if invalid.

        """
        expected_error = URLField.default_error_messages['invalid']
        response = self.client.get(self.url, {'url': 'invalid URL'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFormError(response, 'form', 'url', [expected_error])


class ReviewStatusEmailCommandTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.site_settings = SiteSettings.objects.get_current()
        self.admin = self.create_user('admin', 'admin', email='test@example.com')
        self.site_settings.admins.add(self.admin)
        self.superuser = self.create_user('superuser', 'superuser',
                                          is_superuser=True, email='test@example.com')

        # Clear welcome emails from outbox.
        mail.outbox = []

        # Create three videos submitted two days ago.
        when_submitted = datetime.datetime.now() - datetime.timedelta(2)
        for i in range(3):
            video = self.create_video(status=Video.UNAPPROVED)
            video.when_submitted = when_submitted
            video.save()

    def _set_notification(self, user, send):
        notice_type = notification.NoticeType.objects.get(label='admin_queue_daily')
        setting = notification.get_notification_setting(user, notice_type, "1")
        setting.send = send
        setting.save()

    def test_no_email(self):
        """
        If admins are subscribed, but no videos are new in the previous day,
        no e-mail should be sent.

        """
        self._set_notification(self.admin, True)
        self._set_notification(self.superuser, True)
        review_status_email.Command().handle_noargs()
        self.assertEqual(len(mail.outbox), 0)

    def test_email(self):
        """
        If there is a video submitted in the previous day, an e-mail should be
        sent
        """
        self._set_notification(self.admin, True)
        self._set_notification(self.superuser, True)
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
                          'Video Submissions for example.com')
        t = loader.get_template('localtv/submit_video/review_status_email.txt')
        c = Context({'queue_videos': queue_videos,
                     'new_videos': queue_videos.filter(pk=new_video.pk),
                     'time_period': 'today',
                     'site': Site.objects.get_current()})
        self.assertEqual(message.body, t.render(c))

    def test_no_email_without_setting(self):
        """
        If no admins are subscribed, no e-mail should be sent.
        """
        self._set_notification(self.admin, False)
        self._set_notification(self.superuser, False)

        queue_videos = Video.objects.filter(
            status=Video.UNAPPROVED)

        new_video = queue_videos[0]
        new_video.when_submitted = datetime.datetime.now()
        new_video.save()

        review_status_email.Command().handle_noargs()
        self.assertEqual(len(mail.outbox), 0)


class SubmitVideoViewFunctionalTestCase(BaseTestCase):
    direct_link_data = {
        'url': reverse_lazy('localtv_submit_directlink_video'),
        'template_name': 'localtv/submit_video/direct.html',
        'video_data': {
            'url': 'http://blip.tv/file/get/Miropcf-Miro20Introduction119.mp4'
        },
        'POST': {
            'name': 'name',
            'description': 'description',
            'thumbnail': 'http://www.getmiro.com/favicon.ico',
            'website_url': 'http://www.getmiro.com/',
            'tags': 'tag1, tag2',
            'contact': 'Foo <bar@example.com>',
            'notes': "here's a note!"
        }
    }
    scraped_data = {
        'url': reverse_lazy('localtv_submit_scraped_video'),
        'template_name': 'localtv/submit_video/scraped.html',
        'video_data': {
            'url': 'http://blip.tv/searching-for-mike/fixing-otter-267',
            'title': 'Fixing Otter',
            'embed_code': 'hi',
            'description': (u"<p>In my first produced vlog, I "
                            u"talk a bit about breaking blip.tv,"
                            u" and fixing it. The audio's "
                            u"pretty bad, sorry about that.</p>"),
            'thumbnail_url': 'http://a.images.blip.tv/11156136631.95334664852457-424.jpg',
        },
        'POST': {
            'tags': 'tag1, tag2',
            'contact': 'Foo <bar@example.com>',
            'notes': "here's a note!"
        }
    }
    embed_request_data = {
        'url': reverse_lazy('localtv_submit_embedrequest_video'),
        'template_name': 'localtv/submit_video/embed.html',
        'video_data': {
            'url': 'http://getmiro.com/',
        },
        'POST': {
            'name': 'name',
            'description': 'description',
            'thumbnail': 'http://www.getmiro.com/favicon.ico',
            'embed_code': '<h1>hi!</h1>',
            'tags': 'tag1, tag2',
            'contact': 'Foo <bar@example.com>',
            'notes': "here's a note!"
        }
    }
    old_embed_request_data = embed_request_data.copy()
    old_embed_request_data['POST'] = embed_request_data['POST'].copy()
    old_embed_request_data['POST']['embed'] = embed_request_data['POST']['embed_code']
    del old_embed_request_data['POST']['embed_code']

    def setUp(self):
        BaseTestCase.setUp(self)
        # If the session cookie isn't set, no session store object is returned,
        # which means that you can't modify the session. See django tickets:
        # https://code.djangoproject.com/ticket/11475
        # https://code.djangoproject.com/ticket/10899
        self.client.cookies[settings.SESSION_COOKIE_NAME] = '1'
        session = self.client.session
        session['test'] = 'hi'
        del session['test']
        session.save()
        self.client.cookies[
            settings.SESSION_COOKIE_NAME] = session._session_key
        patcher = patch.object(video_save_thumbnail, 'delay')
        patcher.start()
        self.addCleanup(patcher.stop)

    def _set_session(self, data):
        video = VidscraperVideo(data['video_data']['url'])
        for attr, value in data['video_data'].iteritems():
            setattr(video, attr, value)
        session = self.client.session
        session[SubmitURLView.session_key] = {
            'video': video,
            'url': video.url
        }
        session.save()

    def _test_get__no_session(self, data):
        """
        A GET request to a SubmitVideoView without any session is expected to
        redirect the user back to the SubmitUrlView.

        """
        response = self.client.get(data['url'])
        self.assertRedirects(response, reverse('localtv_submit_video'))

    def test_get__no_session__direct_link(self):
        self._test_get__no_session(self.direct_link_data)

    def test_get__no_session__scraped(self):
        self._test_get__no_session(self.scraped_data)

    def test_get__no_session__embed_request(self):
        self._test_get__no_session(self.embed_request_data)

    def _test_get__simple(self, data):
        """
        A GET request to a SubmitVideoView with correct session data is
        expected to render the correct template containing an unbound form of
        the correct type.

        """
        self._set_session(data)
        response = self.client.get(data['url'])
        self.assertEqual(response.status_code, 200)
        self.assertTrue('form' in response.context[0])
        self.assertFalse(response.context['form'].is_bound)
        self.assertIsInstance(response.context['form'],
                              forms.SubmitVideoFormBase)

    def test_get__simple__direct_link(self):
        self._test_get__simple(self.direct_link_data)

    def test_get__simple__scraped(self):
        self._test_get__simple(self.scraped_data)

    def test_get__simple__embed_request(self):
        self._test_get__simple(self.embed_request_data)

    def test_get__simple__old_embed_request(self):
        self._test_get__simple(self.old_embed_request_data)

    def _test_submit__succeed(self, data, username=None, password=None,
                              approve=False):
        """
        A POST request with correct session data and correct POST data should
        create a video, delete the session data, and redirect the user to the
        submit_thanks view.

        """
        self._set_session(data)

        if username and password:
            self.client.login(username=username, password=password)

        self.assertEqual(len(mail.outbox), 0)
        response = self.client.post(data['url'], data['POST'])
        self.assertEqual(len(Video.objects.all()), 1)
        video = Video.objects.all()[0]

        self.assertRedirects(response, reverse('localtv_submit_thanks',
                                               args=[video.pk]))
        if approve:
            self.assertEqual(video.status, Video.ACTIVE)
        else:
            self.assertEqual(video.status, Video.UNAPPROVED)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(SubmitURLView.session_key in self.client.session)

    def _test_submit__succeed__user(self, data):
        self.create_user('user', 'password')
        self._test_submit__succeed(data, 'user', 'password', approve=False)

    def test_submit__succeed__user__directlink(self):
        self._test_submit__succeed__user(self.direct_link_data)

    def test_submit__succeed__user__scraped(self):
        self._test_submit__succeed__user(self.scraped_data)

    def test_submit__succeed__user__embed_request(self):
        self._test_submit__succeed__user(self.embed_request_data)

    def test_submit__succeed__user__old_embed_request(self):
        self._test_submit__succeed__user(self.old_embed_request_data)

    def _test_submit__succeed__admin(self, data):
        """The video should be approved if the user is an admin."""
        site_settings = SiteSettings.objects.get_current()
        site_settings.admins.add(self.create_user('admin', 'admin'))
        self._test_submit__succeed(data, 'admin', 'admin', approve=True)

    def test_submit__succeed__admin__directlink(self):
        self._test_submit__succeed__admin(self.direct_link_data)

    def test_submit__succeed__admin__scraped(self):
        self._test_submit__succeed__admin(self.scraped_data)

    def test_submit__succeed__admin__embed_request(self):
        self._test_submit__succeed__admin(self.embed_request_data)

    def _test_submit__succeed__notification__user(self, data):
        """
        If the POST to the view succeeds, any admins who are subscribed to the
        'admin_new_submission' notice should be sent an e-mail, unless the user
        submitting the video was an admin.

        """
        self.create_user('user', 'password')
        site_settings = SiteSettings.objects.get_current()
        admin = self.create_user('admin', 'admin', email='test@example.com')
        site_settings.admins.add(admin)
        self._set_session(data)
        self.client.login(username='user', password='password')

        notice_type = notification.NoticeType.objects.get(
            label='admin_new_submission')
        setting = notification.get_notification_setting(admin, notice_type, "1")
        setting.send = True
        setting.save()

        mail.outbox = []

        self.client.post(data['url'], data['POST'])

        self.assertEqual(len(Video.objects.all()), 1)
        video = Video.objects.all()[0]

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        for recipient in message.to:
            u = User.objects.get(email=recipient)
            self.assertTrue(site_settings.user_is_admin(u))

        self.assertEqual(message.subject,
                         '[%s] New Video in Review Queue: %s' % (
                         video.site.name, video))

        t = loader.get_template('localtv/submit_video/new_video_email.txt')
        c = Context({'video': video})
        self.assertEqual(message.body, t.render(c))

    def test_submit__succeed__notification__user__directlink(self):
        self._test_submit__succeed__notification__user(self.direct_link_data)

    def test_submit__succeed__notification__user__scraped(self):
        self._test_submit__succeed__notification__user(self.scraped_data)

    def test_submit__succeed__notification__user__embed_request(self):
        self._test_submit__succeed__notification__user(self.embed_request_data)

    def _test_submit__succeed__notification__admin(self, data):
        site_settings = SiteSettings.objects.get_current()
        site_settings.admins.add(self.create_user('admin', 'admin', email='test@example.com'))
        self._set_session(data)
        self.client.login(username='admin', password='admin')
        mail.outbox = []
        self.client.post(data['url'], data['POST'])
        self.assertEqual(len(mail.outbox), 0)

    def test_submit__succeed__notification__admin__directlink(self):
        self._test_submit__succeed__notification__admin(self.direct_link_data)

    def test_submit__succeed__notification__admin__scraped(self):
        self._test_submit__succeed__notification__admin(self.scraped_data)

    def test_submit__succeed__notification__admin__embed_request(self):
        self._test_submit__succeed__notification__admin(self.embed_request_data)

    def _test_submit__existing_rejected(self, data):
        """
        If the URL represents an existing but rejected video, the rejected
        video should be deleted to allow a resubmission - which happens
        immediately.

        """
        self._set_session(data)
        # We set file_url and website_url so that the session_url will catch
        # no matter which kind of view it is.
        rejected_video = Video.objects.create(
            site=Site.objects.get_current(),
            status=Video.REJECTED,
            name='test video',
            file_url=data['video_data']['url'],
            website_url=data['video_data']['url'])

        response = self.client.post(data['url'], data['POST'])

        self.assertEqual(len(Video.objects.all()), 1)
        video = Video.objects.get()
        self.assertNotEqual(rejected_video, video)

        self.assertRedirects(response, reverse('localtv_submit_thanks',
                                               args=[video.pk]))
        self.assertEqual(video.status, Video.UNAPPROVED)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(SubmitURLView.session_key in self.client.session)

    def test_submit__existing_rejected__directlink(self):
        self._test_submit__existing_rejected(self.direct_link_data)

    def test_submit__existing_rejected__scraped(self):
        self._test_submit__existing_rejected(self.scraped_data)

    def test_submit__existing_rejected__embed_request(self):
        self._test_submit__existing_rejected(self.embed_request_data)

    def _test_submit__existing_unrejected(self, data):
        """
        If the URL represents an existing and unrejected video, it should
        cause the form to be marked invalid.

        """
        self._set_session(data)
        expected_error = "That video has already been submitted!"
        # We set file_url and website_url so that the session_url will catch
        # no matter which kind of view it is.
        unrejected_video = Video.objects.create(
            site=Site.objects.get_current(),
            status=Video.ACTIVE,
            name='test video',
            file_url=data['video_data']['url'],
            website_url=data['video_data']['url'])

        response = self.client.post(data['url'], data['POST'])

        self.assertEqual(len(Video.objects.all()), 1)
        video = Video.objects.get()
        self.assertEqual(video, unrejected_video)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(SubmitURLView.session_key in self.client.session)
        self.assertFormError(response, 'form', None, [expected_error])

    def test_submit__existing_unrejected__directlink(self):
        self._test_submit__existing_unrejected(self.direct_link_data)

    def test_submit__existing_unrejected__scraped(self):
        self._test_submit__existing_unrejected(self.scraped_data)

    def test_submit__existing_unrejected__embed_request(self):
        self._test_submit__existing_unrejected(self.embed_request_data)
