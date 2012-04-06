# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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
from django.core.files import File
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from vidscraper.suites.base import Video as VidscraperVideo

from localtv.models import Video, SiteSettings
from localtv.signals import submit_finished
from localtv.submit_video import forms
from localtv.submit_video.views import (_has_submit_permissions, SubmitURLView,
                                        ScrapedSubmitVideoView,
                                        EmbedSubmitVideoView,
                                        DirectLinkSubmitVideoView)
from localtv.tests.base import BaseTestCase
from localtv.utils import get_or_create_tags


class SubmitPermissionsTestCase(BaseTestCase):
    """
    Test case for submit permissions.

    """
    fixtures = ['users']
    def setUp(self):
        BaseTestCase.setUp(self)
        self.site_settings = SiteSettings.objects.get()
        url = reverse('localtv_submit_video')
        self.anonymous_request = self.factory.get(url)
        self.user_request = self.factory.get(
            url, user=User.objects.get(username='user'))
        self.admin_request = self.factory.get(
            url, user=User.objects.get(username='admin'))

    def test_all_permitted(self):
        """
        If login is not required, all requests should pass the permissions
        check.

        """
        self.site_settings.submission_requires_login = False
        self.site_settings.save()
        self.assertTrue(_has_submit_permissions(self.anonymous_request))
        self.assertTrue(_has_submit_permissions(self.user_request))
        self.assertTrue(_has_submit_permissions(self.admin_request))

    def test_login_required(self):
        """
        If login is required and a submit button is available, all logged-in
        requests should pass the permissions check.

        """
        self.site_settings.submission_requires_login = True
        self.site_settings.display_submit_button = True
        self.site_settings.save()
        self.assertFalse(_has_submit_permissions(self.anonymous_request))
        self.assertTrue(_has_submit_permissions(self.user_request))
        self.assertTrue(_has_submit_permissions(self.admin_request))

    def test_admin_required(self):
        """
        If login is required and no submit button is displayed, only admin
        requests should pass the permissions check.

        """
        self.site_settings.submission_requires_login = True
        self.site_settings.display_submit_button = False
        self.site_settings.save()
        self.assertFalse(_has_submit_permissions(self.anonymous_request))
        self.assertFalse(_has_submit_permissions(self.user_request))
        self.assertTrue(_has_submit_permissions(self.admin_request))


class SubmitURLViewTestCase(BaseTestCase):

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
        Checks that, if the form represents a scraped video, the success_url is
        the url of the scraped_video view, and that the session data contains
        the scraped video as 'video' and the video's url as 'url'.

        """
        view = SubmitURLView()
        video_url = "http://google.com"
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        expected_success_url = "%s?%s" % (
                                reverse('localtv_submit_scraped_video'),
                                view.request.GET.urlencode())
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
        Checks that, if the form represents a direct link to a video file, the
        success_url is the url of the direct_link view, and that the session
        data contains the video (or ``None``) as 'video' and the video's url
        as 'url'.

        NOTE:: Direct link videos will probably not actually result in the
        creation of VidscraperVideo instances; this is tested only to maintain
        the exact behavior which previously existed.

        """
        view = SubmitURLView()
        video_url = "http://google.com/file.mov"
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        expected_success_url = "%s?%s" % (
                                    reverse('localtv_submit_directlink_video'),
                                    view.request.GET.urlencode())
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
        Checks that, if the form represents an embedrequest video - i.e. a video
        that vidscraper can't scrape and which doesn't look like a direct link -
        the success_url is set to the url of the embedrequest view, and that the
        session data contains the scraped video (or ``None``) as 'video' and the
        video's url as 'url'.

        """
        view = SubmitURLView()
        video_url = 'http://google.com'
        url = "%s?url=%s" % (reverse('localtv_submit_video'),
                             video_url)
        view.request = self.factory.get(url)
        expected_success_url = "%s?%s" % (
                                reverse('localtv_submit_embedrequest_video'),
                                view.request.GET.urlencode())
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
        video = self.create_video()
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


class SubmitVideoViewTestCaseMixin(object):
    view_class = None
    POST_data = None

    def setUp(self):
        super(SubmitVideoViewTestCaseMixin, self).setUp()
        self.old_LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL = getattr(settings,
                                    'LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL', None)
        settings.LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL = True
        self.view = self.view_class()

    def tearDown(self):
        super(SubmitVideoViewTestCaseMixin, self).tearDown()
        if self.old_LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL is not None:
            settings.LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL = self.old_LOCALTV_VIDEO_SUBMIT_REQUIRES_EMAIL

    def test_requires_session_data(self):
        # This differs from the functional testing in that it tests the view
        # directly. The inputs given can only result in a 302 response or a 200
        # response, depending on whether there is correct session data or not.
        request = self.factory.get('/')
        response = self.view.dispatch(request)
        self.assertEqual(response.status_code, 302)

        request.session[self.view.get_session_key()] = {
            'url': 'http://google.com',
            'video': VidscraperVideo('http://google.com/')}
        response = self.view.dispatch(request)
        self.assertEqual(response.status_code, 200)

    def test_get_success_url(self):
        self.view.object = self.create_video()
        self.assertEqual(self.view.get_success_url(),
                         reverse('localtv_submit_thanks',
                                 args=[self.view.object.pk]))

    def test_get_initial_tags(self):
        """
        Tests that tags are in the initial data only if tags are defined on the
        video, and that the tags in the expected format - at the moment, this
        is the return value of get_or_create_tags(tags).

        """
        self.view.video = VidscraperVideo('http://google.com')
        initial = self.view.get_initial()
        self.assertFalse('tags' in initial)

        tags = ['hello', 'goodbye']
        self.view.video.tags = tags
        initial = self.view.get_initial()
        self.assertTrue('tags' in initial)
        # This is perhaps not the best way to test this.
        self.assertEqual(initial['tags'], get_or_create_tags(tags))

    def test_form_valid(self):
        """
        Tests that when the form_valid method is run, the session information
        is cleared, and the submit_finished signal is sent.

        """
        self.view.request = self.factory.get('/')
        self.view.object = Video()
        self.view.url = u'http://google.com/'
        self.view.video = VidscraperVideo(self.view.url)
        self.view.video.embed_code = 'Test Code'
        self.view.request.session[self.view.get_session_key()] = {
            'url': self.view.url,
            'video': self.view.video
        }

        submit_dict = {'hit': False}
        def test_submit_finished(sender, **kwargs):
            submit_dict['hit'] = True
        submit_finished.connect(test_submit_finished)
        form = self.view.get_form_class()(data={'url': self.view.url,
                                                'name': 'Test Video',
                                                'embed_code': 'Test Code',
                                                'contact': 'test@test.com'},
                                          **self.view.get_form_kwargs())
        self.assertTrue(form.is_valid(), form.errors.items())
        self.assertTrue(self.view.form_valid(form))

        self.assertEqual(submit_dict['hit'], True)
        self.assertFalse(
            self.view.get_session_key() in self.view.request.session)
        submit_finished.disconnect(test_submit_finished)

    def test_compatible_context(self):
        """
        Tests that the get_context_data method supplies a backwards-compatible
        "data" context variable in addition to adding the form and video to the
        context.

        """
        self.view.request = self.factory.get('/')
        self.view.request.session[self.view.get_session_key()] = {
            'url': '',
            'video': VidscraperVideo('')
            }
        self.view.object = self.create_video()
        self.view.url = (self.view.object.website_url or
                         self.view.object.file_url)
        self.view.video = VidscraperVideo(self.view.url)
        form = self.view.get_form_class()(**self.view.get_form_kwargs())

        context_data = self.view.get_context_data(form=form)
        self.assertEqual(context_data.get('video'), self.view.object)
        self.assertIsInstance(context_data.get('form'), self.view.form_class)
        self.assertTrue('data' in context_data)
        self.assertEqual(set(context_data['data']),
                         set(['link', 'publish_date', 'tags', 'title',
                              'description', 'thumbnail_url', 'user',
                              'user_url']))


class ScrapedSubmitVideoViewTestCase(SubmitVideoViewTestCaseMixin,
                                     BaseTestCase):

    view_class = ScrapedSubmitVideoView

    def test_get_form_class(self):
        """
        Tests that a form for a scraped video only provides the most basic
        fields for additional information.

        """
        self.view.request = self.factory.get('/')
        expected_fields = set(['tags', 'contact', 'notes'])
        self.view.request.session[self.view.get_session_key()] = {
            'url': '',
            'video': VidscraperVideo('http://google.com/')
        }
        form_class = self.view.get_form_class()
        self.assertEqual(set(form_class.base_fields),
                         expected_fields)
        self.assertIsInstance(self.view.object, Video)

    def test_get_object(self):
        """
        Test that `ScrapedSubmitVideoSelf.View.get_object()` actually creates a
        video from the given `vidscraper.suites.base.Video` object.
        """
        self.view.video = VidscraperVideo('http://google.com')
        self.view.video.title = 'Title'
        self.view.video.embed_code = 'embed_code'
        obj = self.view.get_object()
        self.assertEqual(obj.name, 'Title')
        self.assertEqual(obj.embed_code, 'embed_code')

    def test_get_template_names(self):
        """
        Tests that if the video is a scraped video, the scraped video template
        will be used.

        """
        expected_template_names = ['localtv/submit_video/scraped.html']
        self.assertEqual(self.view.get_template_names(),
                         expected_template_names)


class EmbedSubmitVideoViewTestCase(SubmitVideoViewTestCaseMixin, BaseTestCase):

    view_class = EmbedSubmitVideoView

    def test_get_form_class(self):
        """
        Tests that a form for an embedrequest video - i.e. a video that
        vidscraper can't parse and which doesn't look like a direct link -
        provides name, description, thumbnail_url, and embed_code fields in
        addition to the basic fields.

        """
        self.view.request = self.factory.get('/')
        expected_fields = set(['tags', 'contact', 'thumbnail_file', 'notes',
                               'name', 'description', 'embed_code',
                               'thumbnail_url'])

        self.view.request.session[self.view.get_session_key()] = {
            'url': '',
            'video': None
        }
        form_class = self.view.get_form_class()
        self.assertEqual(set(form_class.base_fields),
                         expected_fields)
        self.assertIsInstance(self.view.object, Video)

    def test_get_template_names(self):
        """
        Tests that if the video is an embedrequest video - i.e. a video that
        vidscraper can't parse and which doesn't look like a direct link - the
        embedrequest template will be used.

        """
        self.assertEqual(self.view.get_template_names(),
                         ['localtv/submit_video/embed.html'])


class DirectLinkSubmitVideoViewTestCase(SubmitVideoViewTestCaseMixin,
                                        BaseTestCase):

    view_class = DirectLinkSubmitVideoView

    def test_get_form_class(self):
        """
        Tests that a form for a direct link provides name, description,
        thumbnail_url, and website_url fields in addition to the basic fields.

        """
        self.view.request = self.factory.get('/')
        expected_fields = set(['tags', 'contact', 'thumbnail_file', 'notes',
                               'name', 'description', 'website_url',
                               'thumbnail_url'])
        self.view.request.session[self.view.get_session_key()] = {
            'url': '',
            'video': None
        }
        form_class = self.view.get_form_class()
        self.assertEqual(set(form_class.base_fields),
                         expected_fields)
        self.assertIsInstance(self.view.object, Video)

    def test_get_template_names(self):
        """
        Tests that if the video is a direct link, the direct link template
        will be used.

        """
        expected_template_names = ['localtv/submit_video/direct.html']
        self.assertEqual(self.view.get_template_names(),
                         expected_template_names)


class SubmitVideoFormBaseTestCase(BaseTestCase):
    def setUp(self):

        BaseTestCase.setUp(self)
        self.form_class = modelform_factory(Video, forms.SubmitVideoFormBase)

    def test_sanitize_description(self):
        """
        Tests that the video description is sanitized, and that in
        particular, img tags are removed.

        """
        request = self.factory.get('/')
        form = self.form_class(request, 'http://google.com')
        form.cleaned_data = {'description': "<img src='http://www.google.com/' alt='this should be stripped' />"}
        self.assertEqual(form.clean_description(), '')


class ThumbnailSubmitVideoFormTestCase(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        self.form_class = modelform_factory(Video,
                                            forms.ThumbnailSubmitVideoForm)

    def test_thumbnail_file_override(self):
        """
        Tests that if a thumbnail_file is given to the form, it will override
        the thumbnail_url.

        """
        request = self.factory.get('/')
        form = self.form_class(request, 'http://google.com')
        form.cleaned_data = {
            'thumbnail_file': File(file(self._data_file('logo.png'))),
            'thumbnail_url': 'http://google.com'
        }
        video = form.save()
        self.assertTrue(video.has_thumbnail)
        self.assertEqual(video.thumbnail_url, '')
        self.assertEqual(video.thumbnail_extension, 'png')
