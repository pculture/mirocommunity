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

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from vidscraper.suites import Video as VidscraperVideo

from localtv.models import Video
from localtv.submit_video.views import _has_submit_permissions, SubmitURLView
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
        video_url = "http://google.com"
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        form = view.get_form(view.get_form_class())

        video = VidscraperVideo(video_url)
        video.embed_code = "blink"
        form.video_cache = video
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, "%s?%s" % (
                             reverse('localtv_submit_scraped_video'),
                             view.request.GET.urlencode()))

    def test_form_valid__directlink(self):
        """
        Checks that the success_url and session data are correctly set if the
        form represents a direct link to a video file.

        """
        view = SubmitURLView()
        video_url = "http://google.com/file.mov"
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        form = view.get_form(view.get_form_class())

        form.video_cache = None
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': None, 'url': video_url})
        self.assertEqual(view.success_url, "%s?%s" % (
                             reverse('localtv_submit_directlink_video'),
                             view.request.GET.urlencode()))


    def test_form_valid__embedrequest(self):
        """
        Checks that the success_url and session data are correctly set if the
        form represents an embedrequest video - i.e. a video that we can't
        parse.

        """
        view = SubmitURLView()
        video_url = 'http://google.com'
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        form = view.get_form(view.get_form_class())

        form.video_cache = None
        form.cleaned_data = {'url': video_url}

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': None, 'url': video_url})
        self.assertEqual(view.success_url, "%s?%s" % (
                             reverse('localtv_submit_embedrequest_video'),
                             view.request.GET.urlencode()))

    def test_form_valid__incomplete(self):
        """
        Checks that the success_url and session data are correctly set if the
        form represents a video that we can theoretically parse, but which is
        unusable because of incomplete data.

        """
        view = SubmitURLView()
        video_url = 'http://google.com'
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        form = view.get_form(view.get_form_class())
        form.cleaned_data = {'url': video_url}

        video = VidscraperVideo(video_url)
        form.video_cache = video

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, "%s?%s" % (
                             reverse('localtv_submit_embedrequest_video'),
                             view.request.GET.urlencode()))

        video.file_url = 'hola'
        video.file_url_expires = datetime.datetime.now() + datetime.timedelta(1)

        view.form_valid(form)
        self.assertEqual(view.request.session[view.get_session_key()],
                         {'video': video, 'url': video_url})
        self.assertEqual(view.success_url, "%s?%s" % (
                             reverse('localtv_submit_embedrequest_video'),
                             view.request.GET.urlencode()))

    def test_get_context_data(self):
        """
        Make sure that ``was_duplicate`` and ``video`` are context variables
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
