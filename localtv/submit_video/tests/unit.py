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

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from vidscraper.suites import Video as VidscraperVideo

from localtv.models import Video
from localtv.submit_video.views import (_has_submit_permissions, SubmitURLView,
                                        SubmitVideoView)
from localtv.tests import BaseTestCase


class SubmitPermissionsTestCase(BaseTestCase):
    """
    Test case for submit permissions.

    """
    def setUp(self):
        BaseTestCase.setUp(self)
        url = reverse('localtv_submit_video')
        self.anonymous_request = self.factory.get(url)
        self.user_request = self.factory.get(url)
        self.admin_request = self.factory.get(url)

        self.user_request.user = User.objects.get(username='user')
        self.admin_request.user = User.objects.get(username='admin')

    def test_all_permitted(self):
        """
        If login is not required, all requests should pass the permissions
        check.

        """
        self.site_location.submission_requires_login = False
        self.site_location.save()
        self.assertTrue(_has_submit_permissions(self.anonymous_request))
        self.assertTrue(_has_submit_permissions(self.user_request))
        self.assertTrue(_has_submit_permissions(self.admin_request))

    def test_login_required(self):
        """
        If login is required and a submit button is available, all logged-in
        requests should pass the permissions check.

        """
        self.site_location.submission_requires_login = True
        self.site_location.display_submit_button = True
        self.site_location.save()
        self.assertFalse(_has_submit_permissions(self.anonymous_request))
        self.assertTrue(_has_submit_permissions(self.user_request))
        self.assertTrue(_has_submit_permissions(self.admin_request))

    def test_admin_required(self):
        """
        If login is required and no submit button is displayed, only admin
        requests should pass the permissions check.

        """
        self.site_location.submission_requires_login = True
        self.site_location.display_submit_button = False
        self.site_location.save()
        self.assertFalse(_has_submit_permissions(self.anonymous_request))
        self.assertFalse(_has_submit_permissions(self.user_request))
        self.assertTrue(_has_submit_permissions(self.admin_request))


class SubmitURLViewTestCase(BaseTestCase):
    fixtures = BaseTestCase.fixtures + ['videos']

    def test_GET_submission(self):
        """
        Form data should be captured from the GET parameters.

        """
        view = SubmitURLView()
        url = "%s?%s" % (reverse('localtv_submit_video'),
                         "url=http://google.com")
        view.request = self.factory.get(url)
        form = view.get_form(view.get_form_class())
        self.assertEqual(form.data, view.request.GET)

    def test_form_valid__scraped(self):
        """
        Checks that the success_url and session data are correctly set if the
        form represents a scraped video.

        """
        view = SubmitURLView()
        expected_success_url = "%s?%s" % (
                                reverse('localtv_submit_scraped_video'),
                                view.request.GET.urlencode())
        video_url = "http://google.com"
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        form = view.get_form(view.get_form_class())

        # Option one: Video with embed code
        video = VidscraperVideo(video_url)
        video.embed_code = "blink"
        form.video_cache = video
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)

        # Option two: Video with non-expiring file_url.
        video.embed_code = None
        video.file_url = "blink"

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)


    def test_form_valid__directlink(self):
        """
        Checks that the success_url and session data are correctly set if the
        form represents a direct link to a video file.

        """
        view = SubmitURLView()
        video_url = "http://google.com/file.mov"
        expected_success_url = "%s?%s" % (
                                    reverse('localtv_submit_directlink_video'),
                                    view.request.GET.urlencode())
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        form = view.get_form(view.get_form_class())

        # Option one: No video, but a video file url.
        form.video_cache = None
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': None, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)

        # Option two: A video missing embed_code and file_url data, but a video
        # file url.
        video = VidscraperVideo(video_url)
        form.video_cache = video
        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)


    def test_form_valid__embedrequest(self):
        """
        Checks that the success_url and session data are correctly set if the
        form represents an embedrequest video - i.e. a video that we can't
        scrape and which doesn't look like a direct link.

        """
        view = SubmitURLView()
        expected_success_url = "%s?%s" % (
                                reverse('localtv_submit_embedrequest_video'),
                                view.request.GET.urlencode())
        video_url = 'http://google.com'
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        form = view.get_form(view.get_form_class())

        # Option 1: no video
        form.video_cache = None
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': None, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)

        # Option two: video missing embed & file_url
        video = VidscraperVideo(video_url)
        form.video_cache = video
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)

        # Option three: video with expiring file_url.
        video.file_url = 'hola'
        video.file_url_expires = datetime.datetime.now() + datetime.timedelta(1)

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, expected_success_url)

    def test_get_context_data(self):
        """
        Makes sure that ``was_duplicate`` and ``video`` are context variables
        taken from attributes on the form instance. The setting of those
        attributes is tested in the form unit tests.

        """
        video = Video.objects.all()[0]
        url = video.website_url or video.file_url or video.guid
        view = SubmitURLView()
        form = view.form_class(data={'url': url})

        form.was_duplicate = True
        form.duplicate_video = video
        context = view.get_context_data(form=form)
        self.assertTrue('was_duplicate' in context)
        self.assertTrue('video' in context)
        self.assertEqual(context['was_duplicate'], True)
        self.assertEqual(context['video'], video)


class SubmitVideoViewTestCase(BaseTestCase):
    base_fields = set(['url', 'tags', 'contact', 'thumbnail_file', 'notes'])
    fixtures = BaseTestCase.fixtures + ['videos']

    def setUp(self):
        BaseTestCase.setUp(self)
        self.old_LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL = getattr(settings,
                                    'LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL', None)
        settings.LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL = True

    def tearDown(self):
        BaseTestCase.tearDown(self)
        if self.old_LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL is not None:
            settings.LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL = self.old_LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL

    def test_requires_session_data(self):
        # This differs from the functional testing in that it tests the view
        # directly. The inputs given can only result in a 302 response or a 200
        # response, depending on whether there is correct session data or not.
        view = SubmitVideoView()
        request = self.factory.get('/')
        response = view.dispatch(request)
        self.assertEqual(response.status_code, 302)

        request.session[view.get_session_key()] = {'url': 'http://google.com',
                                                   'video': None}
        response = view.dispatch(request)
        self.assertEqual(response.status_code, 200)

    def test_get_success_url(self):
        obj = Video.objects.all()[0]
        view = SubmitVideoView()
        view.object = obj
        self.assertEqual(view.get_success_url(),
                         reverse('localtv_submit_thanks', args=[obj.pk]))

    def test_get_form_class__scraped(self):
        """
        Tests whether fields are correctly defined for the form based on a
        scraped video.

        """
        view = SubmitVideoView()
        view.request = self.factory.get('/')
        expected_fields = self.base_fields
        video = VidscraperVideo('http://google.com')

        # Option one: Video with embed code
        video.embed_code = 'hola'
        view.request.session[view.get_session_key()] = {
            'url': video.url,
            'video': video
        }
        form_class = view.get_form_class()
        self.assertEqual(set(form_class.base_fields),
                         expected_fields)
        self.assertIsInstance(view.object, Video)

        # Option two: Video with non-expiring file_url.
        video.embed_code = None
        video.file_url = 'hola'
        view.request.session[view.get_session_key()] = {
            'url': video.url,
            'video': video
        }
        form_class = view.get_form_class()
        self.assertEqual(set(form_class.base_fields),
                         expected_fields)
        self.assertIsInstance(view.object, Video)

    def test_get_form_class__directlink(self):
        """
        Tests whether fields are correctly defined for the form based on a
        direct link to a video file.

        """
        view = SubmitVideoView()
        view.request = self.factory.get('/')
        video_url = 'http://google.com/video.mov'
        expected_fields = (self.base_fields |
                           set(['name', 'description', 'website_url']))

        # Option one: No video, but a video file url.
        view.request.session[view.get_session_key()] = {
            'url': video_url,
            'video': None
        }
        form_class = view.get_form_class()
        self.assertEqual(set(form_class.base_fields),
                         expected_fields)
        self.assertIsInstance(view.object, Video)

        # Option two: A video missing embed_code and file_url data, but a video
        # file url.
        video = VidscraperVideo(video_url)
        view.request.session[view.get_session_key()] = {
            'url': video.url,
            'video': video
        }
        form_class = view.get_form_class()
        self.assertEqual(set(form_class.base_fields),
                         expected_fields)
        self.assertIsInstance(view.object, Video)

    def test_get_form_class__embedrequest(self):
        """
        Tests whether fields are correctly defined for the form based on an
        embedrequest video - i.e. a video that we can't parse and which doesn't
        look like a direct link.

        """
        view = SubmitVideoView()
        view.request = self.factory.get('/')
        video_url = 'http://google.com/'
        expected_fields = (self.base_fields |
                           set(['name', 'description', 'embed_code']))

        # Option 1: no video
        view.request.session[view.get_session_key()] = {
            'url': video_url,
            'video': None
        }
        form_class = view.get_form_class()
        self.assertEqual(set(form_class.base_fields),
                         expected_fields)
        self.assertIsInstance(view.object, Video)

        # Option two: video missing embed & file_url
        video = VidscraperVideo(video_url)
        view.request.session[view.get_session_key()] = {
            'url': video.url,
            'video': video
        }
        form_class = view.get_form_class()
        self.assertEqual(set(form_class.base_fields),
                         expected_fields)
        self.assertIsInstance(view.object, Video)

        # Option three: video with expiring file_url.
        video.file_url = 'hola'
        video.file_url_expires = datetime.datetime.now() + datetime.timedelta(1)

        view.request.session[view.get_session_key()] = {
            'url': video.url,
            'video': video
        }
        form_class = view.get_form_class()
        self.assertEqual(set(form_class.base_fields),
                         expected_fields)
        self.assertIsInstance(view.object, Video)
