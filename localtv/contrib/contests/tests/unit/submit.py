from django.core.urlresolvers import reverse
from django.conf import settings

from localtv.contrib.contests.tests.base import BaseTestCase

from vidscraper.videos import Video as VidscraperVideo

from localtv.submit_video.forms import SubmitVideoFormBase
from localtv.models import Video
from localtv.contrib.contests.models import ContestVideo

from localtv.contrib.contests.submit_views import (
    SubmitURLView,
    SubmitVideoView,
    _has_contest_submit_permissions)

class ContestSubmitPermissionsUnit(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.contest = self.create_contest(submissions_open=False)
        self.request = self.factory.get('/')

    def test_submissions_open(self):
        self.contest.submissions_open = True
        self.contest.save()

        self.assertTrue(_has_contest_submit_permissions(
                self.request, self.contest.pk))

    def test_submissions_closed(self):
        self.assertFalse(_has_contest_submit_permissions(
                self.request, self.contest.pk))


    def test_submissions_admin(self):
        admin = self.create_user('admin', is_superuser=True)
        self.request.user = admin

        self.assertTrue(_has_contest_submit_permissions(
                self.request, self.contest.pk))


class ContestSubmitURLViewUnit(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.contest = self.create_contest(submissions_open=True)
        self.view = SubmitURLView()
        self.view.dispatch(self.factory.get('/'),
                           pk=self.contest.pk,
                           slug=self.contest.slug)

    def test_scraped_url(self):
        """
        The scraped URL for this view is the
        'localtv_contests_submit_scraped_video' view.
        """
        self.assertEqual(self.view.scraped_url,
                         reverse('localtv_contests_submit_scraped_video',
                                 args=[self.contest.pk, self.contest.slug]))

    def test_embed_url(self):
        """
        The embed URL for this view is the
        'localtv_contests_submit_embedrequest_video' view.
        """
        self.assertEqual(self.view.embed_url,
                         reverse('localtv_contests_submit_embedrequest_video',
                                 args=[self.contest.pk, self.contest.slug]))

    def test_directlink_url(self):
        """
        The directlink URL for this view is the
        'localtv_contests_submit_directlink_video' view.
        """
        self.assertEqual(self.view.direct_url,
                         reverse('localtv_contests_submit_directlink_video',
                                 args=[self.contest.pk, self.contest.slug]))

    def test_get_session_key(self):
        """
        get_session_key() returns a session key keyed on the current site ID
        and the contest ID."""
        self.assertEqual(self.view.get_session_key(),
                         self.view.session_key_template % (
                settings.SITE_ID, self.contest.pk))

    def test_get_context_data(self):
        """
        get_context_data() includes the :class:`Contest` object under the
        'contest' name.
        """
        context = self.view.get_context_data(form=object())
        self.assertEqual(context['contest'], self.contest)


class ContestSubmitVideoViewUnit(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.contest = self.create_contest(submissions_open=True)
        self.view = SubmitVideoView(form_class=SubmitVideoFormBase,
                                    form_fields=())
        self.view.dispatch(self.factory.get('/'),
                           pk=self.contest.pk,
                           slug=self.contest.slug)

    def test_submit_video_url(self):
        """
        The submit URL for this view is the
        'localtv_contests_submit_video' view.
        """
        self.assertEqual(self.view.submit_video_url,
                         reverse('localtv_contests_submit_video',
                                 args=[self.contest.pk, self.contest.slug]))

    def test_get_success_url(self):
        """
        The success URL for this view is the 'localtv_contests_submit_thanks'
        view.
        """
        self.assertEqual(self.view.get_success_url(),
                         reverse('localtv_contests_submit_thanks',
                                 args=[self.contest.pk, self.contest.slug]))

    def test_form_valid(self):
        """
        If the submitted form is valid, a :class:`ContestVideo` should be
        created for the newly submitted :class:`Video`.
        """
        self.view.request = self.factory.get('/')
        self.view.object = Video()
        self.view.url = u'http://google.com/'
        self.view.video = VidscraperVideo(self.view.url)
        self.view.video.name = 'Test Video'
        self.view.video.embed_code = 'Test Code'
        self.view.request.session[self.view.get_session_key()] = {
            'url': self.view.url,
            'video': self.view.video
            }

        form = self.view.get_form_class()(data={
                'url': self.view.url,
                'name': self.view.video.name,
                'embed_code': self.view.video.embed_code},
                                     **self.view.get_form_kwargs())
        self.assertTrue(form.is_valid(), form.errors.items())
        self.assertTrue(self.view.form_valid(form))
        cv = ContestVideo.objects.get()
        self.assertEqual(cv.video, self.view.object)
        self.assertEqual(cv.contest, self.contest)
