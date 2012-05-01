# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.files.base import File
from django.core.paginator import Page
from django.core import mail
from django.core.urlresolvers import reverse_lazy, reverse
from django.db.models import Q
from django.forms.models import model_to_dict
from django.test.client import Client
from django.utils.encoding import force_unicode
from haystack.query import SearchQuerySet

import mock
from notification import models as notification

from localtv import utils
from localtv.models import Feed, Video, SavedSearch, Category, SiteSettings
from localtv.tests.legacy_localtv import BaseTestCase
import localtv.admin.user_views

Profile = utils.get_profile_model()


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
                if isinstance(data, (list, tuple)):
                    data = [force_unicode(item) for item in data]
                elif data:
                    data = force_unicode(data)
                if data:
                    POST_data[form.add_prefix(name)] = data
        POST_data.update(kwargs)
        return POST_data


# -----------------------------------------------------------------------------
# Approve/reject video tests
# -----------------------------------------------------------------------------


class ApproveRejectAdministrationTestCase(AdministrationBaseTestCase):

    fixtures = BaseTestCase.fixtures + ['feeds', 'videos', 'savedsearches']

    url = reverse_lazy('localtv_admin_approve_reject')

    def test_GET(self):
        """
        A GET request to the approve/reject view should render the
        'localtv/admin/approve_reject_table.html' template.  The
        context should include 'current_video' (the first Video object),
        'page_obj' (a Django Page object), and 'video_list' (a list of the
        Video objects on the current page).
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/approve_reject_table.html')
        self.assertIsInstance(response.context['current_video'],
                              Video)
        self.assertIsInstance(response.context['page_obj'],
                              Page)
        video_list = response.context['video_list']
        self.assertEqual(video_list[0], response.context['current_video'])
        self.assertEqual(len(video_list), 10)

    def test_GET_with_page(self):
        """
        A GET request ot the approve/reject view with a 'page' GET argument
        should return that page of the videos to be approved/rejected.  The
        first page is the 10 oldest videos, the second page is the next 10,
        etc.
        """
        unapproved_videos = Video.objects.filter(status=Video.UNAPPROVED
                                ).order_by('when_submitted', 'when_published')
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        page1_response = c.get(self.url,
                               {'page': '1'})
        self.assertEqual(list(response.context['video_list']),
                          list(page1_response.context['video_list']))
        self.assertEqual(list(page1_response.context['video_list']),
                          list(unapproved_videos[:10]))
        page2_response = c.get(self.url,
                               {'page': '2'})
        self.assertNotEquals(page1_response, page2_response)
        self.assertEqual(list(page2_response.context['video_list']),
                          list(unapproved_videos[10:20]))
        page3_response = c.get(self.url,
                               {'page': '3'}) # doesn't exist, should return
                                              # page 2
        self.assertEqual(list(page2_response.context['video_list']),
                          list(page3_response.context['video_list']))

    def test_GET_preview(self):
        """
        A GET request to the preview_video view should render the
        'localtv/admin/video_preview.html' template and have a
        'current_video' in the context.  The current_video should be the video
        with the primary key passed in as GET['video_id'].
        """
        video = Video.objects.filter(status=Video.UNAPPROVED)[0]
        url = reverse('localtv_admin_preview_video')
        self.assertRequiresAuthentication(url, {'video_id': str(video.pk)})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url,
                         {'video_id': str(video.pk)})
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/video_preview.html')
        self.assertEqual(response.context['current_video'],
                          video)

    def test_GET_approve(self):
        """
        A GET request to the approve_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].
        """
        video = Video.objects.filter(status=Video.UNAPPROVED)[0]
        url = reverse('localtv_admin_approve_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://referer.com')

        video = Video.objects.get(pk=video.pk) # reload
        self.assertEqual(video.status, Video.ACTIVE)
        self.assertTrue(video.when_approved is not None)
        self.assertTrue(video.last_featured is None)

    def test_GET_approve_email(self):
        """
        If the video is approved, and the submitter has the 'video_approved'
        notification on, they should receive an e-mail notifying them of it.
        """
        video = Video.objects.filter(status=Video.UNAPPROVED)[0]
        video.user = User.objects.get(username='user')
        video.save()

        notice_type = notification.NoticeType.objects.get(
            label='video_approved')
        setting = notification.get_notification_setting(video.user,
                                                        notice_type,
                                                        "1")
        setting.send = True
        setting.save()

        url = reverse('localtv_admin_approve_video')

        c = Client()
        c.login(username='admin', password='admin')
        c.get(url, {'video_id': str(video.pk)})

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(),
                          [video.user.email])

    def test_GET_approve_with_feature(self):
        """
        A GET request to the approve_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].  When 'feature' is present in the GET arguments, the
        video should also be featured.
        """
        # XXX why do we have this function
        video = Video.objects.filter(status=Video.UNAPPROVED)[0]
        url = reverse('localtv_admin_approve_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk,
                                                'feature': 'yes'})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk),
                               'feature': 'yes'},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://referer.com')

        video = Video.objects.get(pk=video.pk) # reload
        self.assertEqual(video.status, Video.ACTIVE)
        self.assertTrue(video.when_approved is not None)
        self.assertTrue(video.last_featured is not None)

    def test_GET_reject(self):
        """
        A GET request to the reject_video view should reject the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].
        """
        video = Video.objects.filter(status=Video.UNAPPROVED)[0]
        url = reverse('localtv_admin_reject_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://referer.com')

        video = Video.objects.get(pk=video.pk) # reload
        self.assertEqual(video.status, Video.REJECTED)
        self.assertTrue(video.last_featured is None)

    def test_GET_feature(self):
        """
        A GET request to the feature_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].  If the video is unapproved, it should become
        approved.
        """
        video = Video.objects.filter(status=Video.UNAPPROVED)[0]
        url = reverse('localtv_admin_feature_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://referer.com')

        video = Video.objects.get(pk=video.pk) # reload
        self.assertEqual(video.status, Video.ACTIVE)
        self.assertTrue(video.when_approved is not None)
        self.assertTrue(video.last_featured is not None)

    def test_GET_unfeature(self):
        """
        A GET request to the unfeature_video view should unfeature the video
        and redirect back to the referrer.  The video should be specified by
        GET['video_id'].  The video status is not affected.
        """
        video = Video.objects.filter(status=Video.ACTIVE
                            ).exclude(last_featured=None)[0]

        url = reverse('localtv_admin_unfeature_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://referer.com')

        video = Video.objects.get(pk=video.pk) # reload
        self.assertEqual(video.status, Video.ACTIVE)
        self.assertTrue(video.last_featured is None)

    def test_GET_reject_all(self):
        """
        A GET request to the reject_all view should reject all the videos on
        the given page and redirect back to the referrer.
        """
        unapproved_videos = Video.objects.filter(status=Video.UNAPPROVED)
        page2_videos = unapproved_videos[10:20]

        url = reverse('localtv_admin_reject_all')
        self.assertRequiresAuthentication(url, {'page': 2})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'page': 2},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://referer.com')

        for video in page2_videos:
            self.assertEqual(video.status, Video.REJECTED)

    def test_GET_approve_all(self):
        """
        A GET request to the reject_all view should approve all the videos on
        the given page and redirect back to the referrer.
        """
        unapproved_videos = Video.objects.filter(status=Video.UNAPPROVED)
        page2_videos = unapproved_videos[10:20]

        url = reverse('localtv_admin_approve_all')
        self.assertRequiresAuthentication(url, {'page': 2})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'page': 2},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://referer.com')

        for video in page2_videos:
            self.assertEqual(video.status, Video.ACTIVE)
            self.assertTrue(video.when_approved is not None)


    def test_GET_clear_all(self):
        """
        A GET request to the clear_all view should render the
        'localtv/admin/clear_confirm.html' and have a 'videos' variable
        in the context which is a list of all the unapproved videos.
        """
        unapproved_videos = Video.objects.filter(status=Video.UNAPPROVED,
                                             site=Site.objects.get_current())
        unapproved_videos_count = unapproved_videos.count()

        url = reverse('localtv_admin_clear_all')
        self.assertRequiresAuthentication(url)

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/clear_confirm.html')
        self.assertEqual(list(response.context['videos']),
                          list(unapproved_videos))

        # nothing was rejected
        self.assertEqual(Video.objects.filter(status=Video.UNAPPROVED).count(),
                          unapproved_videos_count)

    def test_POST_clear_all_failure(self):
        """
        A POST request to the clear_all view without POST['confirm'] = 'yes'
        should render the 'localtv/admin/clear_confirm.html' template
        and have a 'videos' variable in the context which is a list of all the
        unapproved videos.
        """
        unapproved_videos = Video.objects.filter(status=Video.UNAPPROVED,
                                             site=Site.objects.get_current())
        unapproved_videos_count = unapproved_videos.count()

        url = reverse('localtv_admin_clear_all')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/clear_confirm.html')
        self.assertEqual(list(response.context['videos']),
                          list(unapproved_videos))

        # nothing was rejected
        self.assertEqual(Video.objects.filter(status=Video.UNAPPROVED).count(),
                          unapproved_videos_count)

    def test_POST_clear_all_succeed(self):
        """
        A POST request to the clear_all view with POST['confirm'] = 'yes'
        should reject all the videos and redirect to the approve_reject view.
        """
        unapproved_videos = Video.objects.filter(status=Video.UNAPPROVED)
        unapproved_videos_count = unapproved_videos.count()

        rejected_videos = Video.objects.filter(status=Video.REJECTED)
        rejected_videos_count = rejected_videos.count()

        url = reverse('localtv_admin_clear_all')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url, {'confirm': 'yes'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver',
                reverse('localtv_admin_approve_reject')))

        # all the unapproved videos are now rejected
        self.assertEqual(Video.objects.filter(status=Video.REJECTED).count(),
                          unapproved_videos_count + rejected_videos_count)


# -----------------------------------------------------------------------------
# Sources administration tests
# -----------------------------------------------------------------------------


class SourcesAdministrationTestCase(AdministrationBaseTestCase):

    fixtures = AdministrationBaseTestCase.fixtures + [
        'feeds', 'savedsearches', 'videos', 'categories']

    url = reverse_lazy('localtv_admin_manage_page')

    def test_GET(self):
        """
        A GET request to the manage_sources view should return a paged view of
        the sources (feeds and saved searches), sorted in alphabetical order.
        It should render the 'localtv/admin/manage_sources.html'
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
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/manage_sources.html')
        self.assertTrue('add_feed_form' in response.context[0])
        self.assertTrue('page' in response.context[0])
        self.assertTrue('headers' in response.context[0])
        self.assertEqual(response.context[0]['search_string'], '')
        self.assertTrue(response.context[0]['source_filter'] is None)
        self.assertEqual(response.context[0]['categories'].model,
                          Category)
        self.assertTrue(response.context[0]['users'].model, User)
        self.assertTrue('successful' in response.context[0])
        self.assertTrue('formset' in response.context[0])

        page = response.context['page']
        self.assertEqual(len(page.object_list), 15)
        self.assertEqual(list(sorted(page.object_list,
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
        self.assertEqual(list(sorted(page.object_list,
                                      key=lambda x:unicode(x).lower())),
                          page.object_list)

        # reversed name
        response = c.get(self.url, {'sort': '-name__lower'})
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:unicode(x).lower())),
                          page.object_list)

        # auto approve
        response = c.get(self.url, {'sort': 'auto_approve'})
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
                                      key=lambda x:x.auto_approve)),
                          page.object_list)

        # reversed auto_approve
        response = c.get(self.url, {'sort': '-auto_approve'})
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:x.auto_approve)),
                          page.object_list)

        # type (feed, search, user)
        response = c.get(self.url, {'sort': 'type'})
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
                                      key=lambda x:x.source_type().lower())),
                          page.object_list)

        # reversed type (user, search, feed)
        response = c.get(self.url, {'sort': '-type'})
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
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
        self.assertEqual(
            list(page.object_list),
            list(SavedSearch.objects.extra({
                        'name__lower': 'LOWER(query_string)'}).order_by(
                    'name__lower')[:10]))

        # feed filter (ignores feeds that represent video service users)
        response = c.get(self.url, {'filter': 'feed'})
        page = response.context['page']
        self.assertEqual(len(page.object_list), 4)
        for feed in page.object_list:
            self.assertTrue(feed.video_service() is None)

        # user filter (only includes feeds that represent video service users)
        response = c.get(self.url, {'filter': 'user'})
        page = response.context['page']
        self.assertEqual(len(page.object_list), 6)
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
        self.assertEqual(len(POST_response.context['formset'].errors[0]), 2)
        self.assertEqual(len(POST_response.context['formset'].errors[1]), 1)

        # make sure the data hasn't changed
        self.assertEqual(POST_data,
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

        feed = Feed.objects.get(pk=POST_data['form-0-id'].split('-')[1])
        feed.save_thumbnail_from_file(File(file(self._data_file('logo.png'))))

        POST_data.update({
                'form-0-name': 'new name!',
                'form-0-feed_url': 'http://pculture.org/',
                'form-0-webpage': 'http://getmiro.com/',
                'form-0-delete_thumbnail': 'yes',
                'form-1-query_string': 'localtv',
                'form-1-thumbnail': File(
                    file(self._data_file('logo.png')))})

        POST_response = c.post(self.url, POST_data,
                               follow=True)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEqual(POST_response.redirect_chain,
                          [('http://%s%s?successful' % (
                        'testserver',
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

        # make sure the data has been updated
        feed = Feed.objects.get(pk=feed.pk)
        self.assertEqual(feed.name, POST_data['form-0-name'])
        self.assertEqual(feed.feed_url, POST_data['form-0-feed_url'])
        self.assertEqual(feed.webpage, POST_data['form-0-webpage'])
        self.assertFalse(feed.has_thumbnail)

        search = SavedSearch.objects.get(
            pk=POST_data['form-1-id'].split('-')[1])
        self.assertEqual(search.query_string,
                          POST_data['form-1-query_string'])
        self.assertTrue(search.has_thumbnail)


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
        self.assertEqual(POST_response.redirect_chain,
                          [('http://%s%s?page=2&successful' % (
                        'testserver',
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

    def test_POST_delete(self):
        """
        A POST request to the manage sources view with a valid formset and a
        DELETE value for a source should remove that source along with all of
        its videos.`
        """
        feed = Feed.objects.get(pk=3)
        saved_search = SavedSearch.objects.get(pk=8)

        for v in Video.objects.all()[:5]:
            v.feed = feed
            v.save()

        for v in Video.objects.all()[5:10]:
            v.search = saved_search
            v.save()

        video_count = Video.objects.count()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)
        POST_data['form-0-DELETE'] = 'yes'
        POST_data['form-1-DELETE'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        self.assertEqual(
            Feed.objects.filter(pk=3).count(), # form 0
            0)

        self.assertEqual(
            SavedSearch.objects.filter(pk=8).count(), # form 1
            0)

        # make sure the 10 videos got removed
        self.assertEqual(Video.objects.count(),
                          video_count - 10)

    def test_POST_delete_keep_videos(self):
        """
        A POST request to the manage source view with a valid formset, a DELETE
        value for a source and a 'keep' POST value, should remove the source
        but keep the videos.
        """
        feed = Feed.objects.get(pk=3)
        saved_search = SavedSearch.objects.get(pk=8)

        for v in Video.objects.all()[:5]:
            v.feed = feed
            v.save()

        for v in Video.objects.all()[5:10]:
            v.search = saved_search
            v.save()

        video_count = Video.objects.count()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)
        POST_data['form-0-DELETE'] = 'yes'
        POST_data['form-1-DELETE'] = 'yes'
        POST_data['keep'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        self.assertEqual(
            Feed.objects.filter(pk=3).count(), # form 0
            0)

        self.assertEqual(
            SavedSearch.objects.filter(pk=8).count(), # form 1
            0)

        # make sure the 10 videos are still there
        self.assertEqual(Video.objects.count(),
                          video_count)

    def test_POST_bulk_edit(self):
        """
        A POST request to the manage_sources view with a valid formset and the
        extra form filled out should update any source with the bulk option
        checked.
        """
        # give the feed a category
        for source in (Feed.objects.get(pk=3), # form 0
                       SavedSearch.objects.get(pk=8)): # form 1
            source.auto_categories =[Category.objects.get(pk=2)]
            source.save()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['form-15-auto_categories'] = [1]
        POST_data['form-15-auto_authors'] = [1, 2]
        POST_data['form-15-auto_approve'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        feed = Feed.objects.get(pk=3) # form 0
        saved_search = SavedSearch.objects.get(pk=8) # form 1

        self.assertEqual(feed.auto_approve, True)
        self.assertEqual(saved_search.auto_approve, True)
        self.assertEqual(
            set(feed.auto_categories.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEqual(
            set(saved_search.auto_categories.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEqual(
            set(feed.auto_authors.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEqual(
            set(saved_search.auto_authors.values_list('pk', flat=True)),
            set([1, 2]))

    def test_POST_bulk_delete(self):
        """
        A POST request to the manage_sources view with a valid formset and a
        POST['bulk_action'] of 'remove' should remove the sources with the bulk
        option checked.
        """
        feed = Feed.objects.get(pk=3)
        saved_search = SavedSearch.objects.get(pk=8)

        for v in Video.objects.all()[:5]:
            v.feed = feed
            v.save()

        for v in Video.objects.all()[5:10]:
            v.search = saved_search
            v.save()

        video_count = Video.objects.count()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['bulk_action'] = 'remove'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        self.assertEqual(
            Feed.objects.filter(pk=3).count(), # form 0
            0)

        self.assertEqual(
            SavedSearch.objects.filter(pk=8).count(), # form 1
            0)

        # make sure the 10 videos got removed
        self.assertEqual(Video.objects.count(),
                          video_count - 10)

    def test_POST_bulk_delete_keep_videos(self):
        """
        A POST request to the manage_sources view with a valid formset, a
        POST['bulk_action'] of 'remove', and 'keep' in the POST data should
        remove the source with the bulk option checked but leave the videos.
        """
        feed = Feed.objects.get(pk=3)
        saved_search = SavedSearch.objects.get(pk=8)

        for v in Video.objects.all()[:5]:
            v.feed = feed
            v.save()

        for v in Video.objects.all()[5:10]:
            v.search = saved_search
            v.save()

        video_count = Video.objects.count()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['bulk_action'] = 'remove'
        POST_data['keep'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        self.assertEqual(
            Feed.objects.filter(pk=3).count(), # form 0
            0)

        self.assertEqual(
            SavedSearch.objects.filter(pk=8).count(), # form 1
            0)

        # make sure the 10 videos got removed
        self.assertEqual(Video.objects.count(),
                          video_count)

    def test_POST_switching_categories_authors(self):
        """
        A POST request to the manage_sources view with a valid formset that
        includes changed categories or authors, videos that had the old
        categories/authors should be updated to the new values.
        """
        feed = Feed.objects.get(pk=3)
        saved_search = SavedSearch.objects.get(pk=8)
        category = Category.objects.get(pk=1)
        user = User.objects.get(pk=1)
        category2 = Category.objects.get(pk=2)
        user2 = User.objects.get(pk=2)

        for v in Video.objects.order_by('pk')[:3]:
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

        for v in Video.objects.order_by('pk')[3:6]:
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
            POST_data['form-%i-BULK'% i] = 'yes'
        POST_data['form-15-auto_categories'] = [category2.pk]
        POST_data['form-15-auto_authors'] = [user2.pk]

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        for v in Video.objects.order_by('pk')[:3]:
            self.assertEqual(v.feed, feed)
            if v.pk == 1:
                # nothing changed
                self.assertEqual(
                    set(v.categories.all()),
                    set([category]))
                self.assertEqual(
                    set(v.authors.all()),
                    set([user]))
            elif v.pk == 2:
                # user changed
                self.assertEqual(
                    set(v.categories.all()),
                    set([category]))
                self.assertEqual(
                    set(v.authors.all()),
                    set([user2]))
            elif v.pk == 3:
                # category changed
                self.assertEqual(
                    set(v.categories.all()),
                    set([category2]))
                self.assertEqual(
                    set(v.authors.all()),
                    set([user]))
            else:
                self.fail('invalid feed video pk: %i' % v.pk)

        for v in Video.objects.order_by('pk')[3:6]:
            self.assertEqual(v.search, saved_search)
            if v.pk == 4:
                # nothing changed
                self.assertEqual(
                    set(v.categories.all()),
                    set([category]))
                self.assertEqual(
                    set(v.authors.all()),
                    set([user]))
            elif v.pk == 5:
                # user changed
                self.assertEqual(
                    set(v.categories.all()),
                    set([category]))
                self.assertEqual(
                    set(v.authors.all()),
                    set([user2]))
            elif v.pk == 6:
                # category changed
                self.assertEqual(
                    set(v.categories.all()),
                    set([category2]))
                self.assertEqual(
                    set(v.authors.all()),
                    set([user]))
            else:
                self.fail('invalid search video pk: %i' % v.pk)


# -----------------------------------------------------------------------------
# Feed Administration tests
# -----------------------------------------------------------------------------


class FeedAdministrationTestCase(BaseTestCase):

    url = reverse_lazy('localtv_admin_feed_add')
    feed_url = "http://participatoryculture.org/feeds_test/feed7.rss"

    def test_GET(self):
        """
        A GET request to the add_feed view should render the
        'localtv/admin/add_feed.html' template.  Context:

        * form: a SourceForm to allow setting auto categories/authors
        * video_count: the number of videos we think we can get out of the feed
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'feed_url': self.feed_url})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/add_feed.html')
        self.assertTrue(response.context[2]['form'].instance.feed_url,
                        self.feed_url)
        self.assertEqual(response.context[2]['video_count'], 1)

    def test_GET_fail_existing(self):
        """
        A GET request to the add_feed view should fail if the feed already
        exists.
        """
        Feed.objects.create(
            site=self.site_settings.site,
            last_updated=datetime.datetime.now(),
            status=Feed.INACTIVE,
            feed_url=self.feed_url)
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'feed_url': self.feed_url})
        self.assertStatusCodeEquals(response, 400) # bad request

    def test_GET_fail_existing_youtube(self):
        """
        We accept a few different kinds of YouTube URLs.  We should make sure
        we only have one feed per base URL.
        """
        urls = [
            ('http://gdata.youtube.com/feeds/base/users/CLPPrj/uploads?'
             'alt=rss&v=2'),
            ('http://gdata.youtube.com/feeds/base/users/CLPPrj/uploads?'
             'alt=rss&v=2&orderby=published'),
            'http://www.youtube.com/rss/user/CLPPrj/videos.rss']
        Feed.objects.create(
            site=self.site_settings.site,
            last_updated=datetime.datetime.now(),
            status=Feed.INACTIVE,
            feed_url=urls[0])
        c = Client()
        c.login(username='admin', password='admin')
        for url in urls:
            response = c.get(self.url, {'feed_url': url})
            self.assertEqual(response.status_code, 400,
                              '%r not stopped as a duplicate' % url)

    def test_GET_vimeo(self):
        """
        A GET request to the add_feed view should render the
        'localtv/admin/add_feed.html' template if the URL is a Vimeo
        User RSS url.
        """
        url = 'http://www.vimeo.com/user1054395/videos/rss'
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'feed_url': url})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/add_feed.html')
        self.assertTrue(response.context[2]['form'].instance.feed_url,
                        url)

    def test_GET_vimeo_channel(self):
        """
        A GET request to the add_feed view should render the
        'localtv/admin/add_feed.html' template if the URL is a Vimeo
        Channel RSS url.
        """
        url = 'http://vimeo.com/channels/sparkyawards/videos/rss'
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'feed_url': url})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/add_feed.html')
        self.assertTrue(response.context[2]['form'].instance.feed_url,
                        url)

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
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/add_feed.html')
        self.assertTrue(response.context[0]['form'].instance.feed_url,
                        self.feed_url)
        self.assertFalse(response.context[0]['form'].is_valid())
        self.assertEqual(response.context[0]['video_count'], 1)

    def test_POST_failure_bad_url(self):
        """
        A POST request to the add_feed view with a non-feed URL should display
        an error message.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url + "?feed_url=http://www.google.com",
                          {'feed_url': "http://www.google.com",
                           'auto_categories': [1]})
        self.assertStatusCodeEquals(response, 400)

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
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver',
                reverse('localtv_admin_manage_page')))

        self.assertEqual(Feed.objects.count(), 0)

    def test_POST_succeed(self):
        """
        A POST request to the add_feed view with a valid form should redirect
        the user to the localtv_admin_manage_page view.

        A Feed object should also be created, but not have any items.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url + "?feed_url=%s" % self.feed_url,
                          {'feed_url': self.feed_url,
                           'auto_approve': 'yes'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver',
                reverse('localtv_admin_manage_page')))

        feed = Feed.objects.get()
        self.assertEqual(feed.name, 'Valid Feed with Relative Links')
        self.assertEqual(feed.feed_url, self.feed_url)
        # if CELERY_ALWAYS_EAGER is True, we'll have imported the feed here
        self.assertTrue(feed.status in (Feed.INACTIVE, Feed.ACTIVE))
        self.assertTrue(feed.auto_approve)

    def test_GET_creates_user(self):
        """
        When creating a new feed from a feed for a user on a video service, a
        User object should be created with that username and should be set as
        the auto-author for that feed.
        """
        url = ("http://gdata.youtube.com/feeds/base/users/mphtower/uploads"
               "?alt=rss&v=2&orderby=published")
        c = Client()
        c.login(username='admin', password='admin')
        c.post(self.url + "?feed_url=%s" % url,
               {'feed_url': url,
                'auto_approve': 'yes'})

        feed = Feed.objects.get()
        user = User.objects.get(username='mphtower')
        self.assertEqual(feed.name, 'mphtower')

        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.email, '')
        self.assertEqual(user.get_profile().website,
                          'http://www.youtube.com/user/mphtower/videos')
        self.assertEqual(list(feed.auto_authors.all()),
                          [user])

    def test_GET_reuses_existing_user(self):
        """
        When creating a feed from a feed for a user on a video servers, if a
        User already exists with the given username, it should be used instead
        of creating a new object.
        """
        user = User.objects.create_user('mphtower', 'mph@tower.com',
                                        'password')
        Profile.objects.create(user=user,
                                      website='http://www.mphtower.com/')

        url = ("http://gdata.youtube.com/feeds/base/users/mphtower/uploads"
               "?alt=rss&v=2&orderby=published")
        c = Client()
        c.login(username='admin', password='admin')
        c.post(self.url + "?feed_url=%s" % url,
               {'feed_url': url,
                'auto_approve': 'yes'})

        user = User.objects.get(username='mphtower') # reload user
        self.assertTrue(user.has_usable_password())
        self.assertEqual(user.email, 'mph@tower.com')
        self.assertEqual(user.get_profile().website,
                          'http://www.mphtower.com/')

        feed = Feed.objects.get()
        self.assertEqual(list(feed.auto_authors.all()),
                          [user])

    def test_GET_auto_approve(self):
        """
        A GET request to the feed_auto_approve view should set the auto_approve
        bit on the feed specified in the URL and redirect back to the referrer.
        It should also require the user to be an administrator.
        """
        feed = Feed.objects.create(site=self.site_settings.site,
                                          name='name',
                                          feed_url='feed_url',
                                          auto_approve=False,
                                          last_updated=datetime.datetime.now(),
                                          status=Feed.ACTIVE)
        url = reverse('localtv_admin_feed_auto_approve', args=(feed.pk,))
        self.assertRequiresAuthentication(url)
        self.assertRequiresAuthentication(url,
                                          username='user',
                                          password='password')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url,
                         HTTP_REFERER='http://www.google.com/')
        self.assertEqual(feed.auto_approve, False)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://www.google.com/')

    def test_GET_auto_approve_disable(self):
        """
        A GET request to the feed_auto_approve view with GET['disable'] set
        should remove the auto_approve bit on the feed specified in the URL and
        redirect back to the referrer.
        """
        feed = Feed.objects.create(site=self.site_settings.site,
                                          name='name',
                                          feed_url='feed_url',
                                          auto_approve=True,
                                          last_updated=datetime.datetime.now(),
                                          status=Feed.ACTIVE)
        url = reverse('localtv_admin_feed_auto_approve', args=(feed.pk,))

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'disable': 'yes'},
                         HTTP_REFERER='http://www.google.com/')
        self.assertEqual(feed.auto_approve, True)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://www.google.com/')


# -----------------------------------------------------------------------------
# Search administration tests
# -----------------------------------------------------------------------------


class SearchAdministrationTestCase(AdministrationBaseTestCase):

    url = reverse_lazy('localtv_admin_search')

    def test_GET(self):
        """
        A GET request to the livesearch view should render the
        'localtv/admin/livesearch_table.html' template.  Context:

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
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/livesearch_table.html')
        self.assertTrue('current_video' in response.context[0])
        self.assertTrue('page_obj' in response.context[0])
        self.assertTrue('query_string' in response.context[0])
        self.assertTrue('order_by' in response.context[0])
        self.assertTrue('is_saved_search' in response.context[0])

    def test_GET_query(self):
        """
        A GET request to the livesearch view and GET['q'] argument should list
        some videos that match the query.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'q': 'search string'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/livesearch_table.html')
        self.assertIsInstance(response.context['current_video'],
                              Video)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(len(response.context['page_obj'].object_list), 10)
        self.assertEqual(response.context['query_string'], 'search string')
        self.assertEqual(response.context['order_by'], 'latest')
        self.assertEqual(response.context['is_saved_search'], False)

    def test_GET_query_pagination(self):
        """
        A GET request to the livesearch view with GET['q'] and GET['page']
        arguments should return another page of results.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'q': 'search string'})
        self.assertEqual(response.context[2]['page_obj'].number, 1)
        self.assertEqual(len(response.context[2]['page_obj'].object_list), 10)

        response2 = c.get(self.url,
                         {'q': 'search string',
                          'page': '2'})
        page_obj = response2.context[2]['page_obj']
        self.assertEqual(page_obj.number, 2)
        if page_obj.has_next():
            self.assertEqual(len(page_obj.object_list), 10)
        else:
            self.assertTrue(page_obj.object_list)

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
        self.assertTrue(c.login(username='admin', password='admin'))
        response = c.get(self.url,
                         {'q': 'search string'})
        fake_video = response.context[2]['page_obj'].object_list[0]
        fake_video2 = response.context[2]['page_obj'].object_list[1]

        response = c.get(reverse('localtv_admin_search_video_approve'),
                         {'q': 'search string',
                          'video_id': fake_video.id},
                         HTTP_REFERER="http://www.getmiro.com/")
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], "http://www.getmiro.com/")

        v = Video.objects.get()
        self.assertEqual(v.site, self.site_settings.site)
        self.assertEqual(v.name, fake_video.name)
        self.assertEqual(v.description, fake_video.description)
        self.assertEqual(v.file_url, fake_video.file_url)
        self.assertEqual(v.embed_code, fake_video.embed_code)
        self.assertTrue(v.last_featured is None)

        user = User.objects.get(username=v.video_service_user)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.get_profile().website,
                          v.video_service_url)
        self.assertEqual(list(v.authors.all()), [user])

        response = c.get(self.url,
                         {'q': 'search string'})
        self.assertEqual(response.context[2]['page_obj'].object_list[0].id,
                          fake_video2.id)

    def test_GET_approve_authentication(self):
        """
        A GET request to the approve view should require that the user is
        authenticated.
        """
        url = reverse('localtv_admin_search_video_approve')

        self.assertRequiresAuthentication(url)
        self.assertRequiresAuthentication(url,
                                          username='user', password='password')

    def test_GET_approve_feature(self):
        """
        A GET request to the approve view should create a new video object from
        the search and redirect back to the referrer.  If GET['feature'] is
        present, the video should also be marked as featured.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'q': 'search string'})
        metasearch_video = response.context[2]['page_obj'].object_list[0]

        response = c.get(reverse('localtv_admin_search_video_approve'),
                         {'q': 'search string',
                          'feature': 'yes',
                          'video_id': metasearch_video.id},
                         HTTP_REFERER="http://www.getmiro.com/")
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], "http://www.getmiro.com/")

        v = Video.objects.get()
        self.assertTrue(v.last_featured is not None)

    def test_GET_display(self):
        """
        A GET request to the display view should render the
        'localtv/admin/video_preview.html' and include the
        MetasearchVideo as 'current_video' in the context.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'q': 'search string'})
        metasearch_video = response.context[2]['page_obj'].object_list[0]

        response = c.get(reverse('localtv_admin_search_video_display'),
                         {'q': 'search string',
                          'video_id': metasearch_video.id})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/video_preview.html')
        self.assertEqual(response.context[0]['current_video'].id,
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
                         {'q': 'search string'},
                         HTTP_REFERER='http://www.getmiro.com/')
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://www.getmiro.com/')

        saved_search = SavedSearch.objects.get()
        self.assertEqual(saved_search.query_string, 'search string')
        self.assertEqual(saved_search.site, self.site_settings.site)
        self.assertEqual(saved_search.user.username, 'admin')

        response = c.get(self.url,
                         {'q': 'search string'})
        self.assertTrue(response.context[2]['is_saved_search'])

    def test_GET_create_saved_search_authentication(self):
        """
        A GET request to the create_saved_search view should require that the
        user is authenticated.
        """
        url = reverse('localtv_admin_search_add')

        self.assertRequiresAuthentication(url)
        self.assertRequiresAuthentication(url,
                                          username='user', password='password')

    def test_GET_search_auto_approve(self):
        """
        A GET request to the search_auto_appprove view should set the
        auto_approve bit to True on the given SavedSearch object and redirect
        back to the referrer
        """
        saved_search = SavedSearch.objects.create(
            site=self.site_settings.site,
            query_string='search string')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_admin_search_auto_approve',
                                 args=[saved_search.pk]),
                         HTTP_REFERER='http://www.getmiro.com/')
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://www.getmiro.com/')

        saved_search = SavedSearch.objects.get(pk=saved_search.pk)
        self.assertTrue(saved_search.auto_approve)

    def test_GET_search_auto_approve_authentication(self):
        """
        A GET request to the search_auto_approve view should require that the
        user is authenticated.
        """
        url = reverse('localtv_admin_search_auto_approve',
                      args=[1])

        self.assertRequiresAuthentication(url)
        self.assertRequiresAuthentication(url,
                                          username='user', password='password')

    def test_GET_search_auto_approve_disable(self):
        """
        A GET request to the search_auto_appprove view with GET['disable'] set
        should set the auto_approve bit to False on the given SavedSearch
        object and redirect back to the referrer
        """
        saved_search = SavedSearch.objects.create(
            site=self.site_settings.site,
            auto_approve=True,
            query_string='search string')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_admin_search_auto_approve',
                                 args=[saved_search.pk]),
                                 {'disable': 'yes'},
                         HTTP_REFERER='http://www.getmiro.com/')
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://www.getmiro.com/')

        saved_search = SavedSearch.objects.get(pk=saved_search.pk)
        self.assertFalse(saved_search.auto_approve)

# -----------------------------------------------------------------------------
# User administration tests
# -----------------------------------------------------------------------------


class UserAdministrationTestCase(AdministrationBaseTestCase):

    url = reverse_lazy('localtv_admin_users')

    def test_GET(self):
        """
        A GET request to the users view should render the
        'localtv/admin/users.html' template and include a formset for
        the users, an add_user_form, and the headers for the formset.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/users.html')
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
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/users.html')
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
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/users.html')
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
            'email': 'new@testserver.local',
            'role': 'user',
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        new = User.objects.order_by('-id')[0]
        for key, value in POST_data.items():
            if key == 'submit':
                pass
            elif key == 'role':
                new_site_settings = SiteSettings.objects.get()
                self.assertFalse(new_site_settings.user_is_admin(new))
            else:
                self.assertEqual(getattr(new, key), value)

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
            'email': 'new@testserver.local',
            'role': 'admin',
            'password_f': 'new_password',
            'password_f2': 'new_password'
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        new = User.objects.order_by('-id')[0]
        for key, value in POST_data.items():
            if key in ('submit', 'password_f', 'password_f2'):
                pass
            elif key == 'role':
                new_site_settings = SiteSettings.objects.get()
                self.assertTrue(new_site_settings.user_is_admin(new))
            else:
                self.assertEqual(getattr(new, key), value)

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
        Profile.objects.create(
            user=user,
            logo=File(file(self._data_file('logo.png'))),
            description='Some description about the user')

        old_users = User.objects.values()
        old_profiles = Profile.objects.values()

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']

        POST_response = c.post(self.url, self._POST_data_from_formset(
                formset,
                submit='Save'))
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        for old, new in zip(old_users, User.objects.values()):
            self.assertEqual(old, new)
        for old, new in zip(old_profiles, Profile.objects.values()):
            self.assertEqual(old, new)

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
        POST_data['form-0-name'] = 'NewFirst NewLast'
        POST_data['form-0-role'] = 'user'
        POST_data['form-1-logo'] = file(self._data_file('logo.png'))
        POST_data['form-1-name'] = ''
        POST_data['form-1-website'] = 'http://google.com/ http://twitter.com/'
        POST_data['form-1-description'] = 'Superuser Description'
        POST_data['form-2-username'] = 'new_admin'
        POST_data['form-2-role'] = 'admin'
        POST_data['form-2-location'] = 'New Location'
        POST_data['form-2-password_f'] = 'new_admin'
        POST_data['form-2-password_f2'] = 'new_admin'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        self.assertEqual(User.objects.count(), 4) # no one got added

        new_admin = User.objects.get(username='new_admin')
        self.assertEqual(new_admin.pk, 1)
        self.assertTrue(self.site_settings.user_is_admin(new_admin))
        self.assertTrue(new_admin.check_password('new_admin'))
        self.assertEqual(new_admin.get_profile().location, 'New Location')

        superuser = User.objects.get(username='superuser')
        self.assertEqual(superuser.pk, 2)
        self.assertEqual(superuser.is_superuser, True)
        self.assertEqual(superuser.first_name, '')
        self.assertEqual(superuser.last_name, '')
        self.assertFalse(superuser in self.site_settings.admins.all())
        self.assertTrue(superuser.check_password('superuser'))
        profile = superuser.get_profile()
        self.assertTrue(profile.logo.name.endswith('logo.png'))
        self.assertEqual(profile.website,
                          'http://google.com/ http://twitter.com/')
        self.assertEqual(profile.description, 'Superuser Description')

        old_admin = User.objects.get(username='admin')
        self.assertEqual(old_admin.pk, 3)
        self.assertEqual(old_admin.first_name, 'NewFirst')
        self.assertEqual(old_admin.last_name, 'NewLast')
        self.assertFalse(self.site_settings.user_is_admin(old_admin))
        self.assertTrue(old_admin.check_password('admin'))

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
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        self.assertEqual(User.objects.count(), 3) # one user got removed

        self.assertEqual(User.objects.filter(username='user').count(), 0)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)

    def test_POST_delete_nonhuman_user(self):
        """
        A POST to the users view with a POST['submit'] of 'Save' and a
        successful formset should update the users data.  If form-*-DELETE is
        present, that user should be removed, unless that user is a superuser.
        """
        # Take the user called "user" and give the user an unusable password
        # this should simulate the person being a nonhuman user.
        
        u = User.objects.get(username='user')
        u.set_unusable_password()
        u.save()
        self.assertEqual(
            3,
            User.objects.filter(localtv.admin.user_views._filter_just_humans()).count())
       
        c = Client()
        c.login(username="admin", password="admin")

        GET_response = c.get(self.url + "?show=all")
        formset = GET_response.context['formset']
        POST_data = self._POST_data_from_formset(formset,
                                                 submit='Save')

        # form-0 is admin (3)
        # form-1 is superuser (2)
        # form-2 is user (1)
        POST_data['form-2-DELETE'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        self.assertEqual(User.objects.count(), 3) # one user got removed

        self.assertEqual(User.objects.filter(username='user').count(), 0)


# -----------------------------------------------------------------------------
# Category administration tests
# -----------------------------------------------------------------------------


class CategoryAdministrationTestCase(AdministrationBaseTestCase):

    fixtures = AdministrationBaseTestCase.fixtures + [
        'categories']

    url = reverse_lazy('localtv_admin_categories')

    def test_GET(self):
        """
        A GET request to the categories view should render the
        'localtv/admin/categories.html' template and include a formset
        for the categories and an add_category_form.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/categories.html')
        self.assertTrue('formset' in response.context[0])
        self.assertTrue('add_category_form' in response.context[0])

    def test_POST_add_failure(self):
        """
        A POST to the categories view with a POST['submit'] value of 'Add' but
        a failing form should rerender the template.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url,
                          {'submit': 'Add'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/categories.html')
        self.assertTrue('formset' in response.context[0])
        self.assertTrue(
            getattr(response.context[0]['add_category_form'],
                    'errors') is not None)

    def test_POST_add_failure_duplicate(self):
        """
        A POST to the categories view with a POST['submit'] value of 'Add' but
        a duplicated category should rerender the template.
        """
        c = Client()
        c.login(username="admin", password="admin")
        POST_data = {
            'submit': 'Add',
            'name': 'Miro',
            'slug': 'miro'
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/categories.html')
        self.assertTrue('formset' in response.context[0])
        self.assertTrue(
            getattr(response.context[0]['add_category_form'],
                    'errors') is not None)

    def test_POST_save_failure(self):
        """
        A POST to the categories view with a POST['submit'] value of 'Save' but
        a failing formset should rerender the template.
        """
        c = Client()
        c.login(username='admin', password='admin')

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']
        POST_data = self._POST_data_from_formset(formset,
                                                 submit='Save')

        POST_data['form-0-name'] = ''

        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/categories.html')
        self.assertTrue(
            getattr(response.context[0]['formset'], 'errors') is not None)
        self.assertTrue('add_category_form' in response.context[0])

    def test_POST_save_failure_short_cycle(self):
        """
        If a change to the categories sets the parent of a category to itself,
        the save should fail.
        """
        c = Client()
        c.login(username="admin", password="admin")

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']
        POST_data = self._POST_data_from_formset(formset,
                                                 submit='Save')

        POST_data['form-0-parent'] = POST_data['form-0-id']

        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/categories.html')
        self.assertTrue(
            getattr(response.context[0]['formset'], 'errors') is not None)
        self.assertTrue('add_category_form' in response.context[0])

    def test_POST_save_failure_long_cycle(self):
        """
        If a change to the categories creates a longer cycle, the save should
        fail.
        """
        c = Client()
        c.login(username="admin", password="admin")

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']
        POST_data = self._POST_data_from_formset(formset,
                                                 submit='Save')

        POST_data['form-0-parent'] = POST_data['form-1-id']
        POST_data['form-1-parent'] = POST_data['form-2-id']
        POST_data['form-1-parent'] = POST_data['form-0-id']

        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/categories.html')
        self.assertTrue(
            getattr(response.context[0]['formset'], 'errors') is not None)
        self.assertTrue('add_category_form' in response.context[0])

    def test_POST_add(self):
        """
        A POST to the categories view with a POST['submit'] of 'Add' and a
        successful form should create a new category and redirect the user back
        to the management page.
        """
        c = Client()
        c.login(username="admin", password="admin")
        POST_data = {
            'submit': 'Add',
            'name': 'new category',
            'slug': 'newcategory',
            'description': 'A New User',
            'logo': file(self._data_file('logo.png')),
            'parent': 1,
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        new = Category.objects.order_by('-id')[0]

        self.assertEqual(new.site, self.site_settings.site)

        for key, value in POST_data.items():
            if key == 'submit':
                pass
            elif key == 'logo':
                new.logo.open()
                value.seek(0)
                self.assertEqual(new.logo.read(), value.read())
            elif key == 'parent':
                self.assertEqual(new.parent.pk, value)
            else:
                self.assertEqual(getattr(new, key), value)

    def test_POST_save_no_changes(self):
        """
        A POST to the categoriess view with a POST['submit'] of 'Save' and a
        successful formset should update the category data.  The default values
        of the formset should not change the values of any of the Categorys.
        """
        c = Client()
        c.login(username="admin", password="admin")

        old_categories = Category.objects.values()

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']

        POST_response = c.post(self.url, self._POST_data_from_formset(
                formset,
                submit='Save'))

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        for old, new in zip(old_categories, Category.objects.values()):
            self.assertEqual(old, new)

    def test_POST_save_changes(self):
        """
        A POST to the categories view with a POST['submit'] of 'Save' and a
        successful formset should update the category data.
        """
        c = Client()
        c.login(username="admin", password="admin")

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']
        POST_data = self._POST_data_from_formset(formset,
                                                 submit='Save')


        POST_data['form-0-name'] = 'New Name'
        POST_data['form-0-slug'] = 'newslug'
        POST_data['form-1-logo'] = file(self._data_file('logo.png'))
        POST_data['form-1-description'] = 'New Description'
        POST_data['form-2-parent'] = 5

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        self.assertEqual(Category.objects.count(), 5) # no one got
                                                              # added

        new_slug = Category.objects.get(slug='newslug')
        self.assertEqual(new_slug.pk, 5)
        self.assertEqual(new_slug.name, 'New Name')

        new_logo = Category.objects.get(slug='miro')
        new_logo.logo.open()
        self.assertEqual(new_logo.logo.read(),
                          file(self._data_file('logo.png')).read())
        self.assertEqual(new_logo.description, 'New Description')

        new_parent = Category.objects.get(slug='linux')
        self.assertEqual(new_parent.parent.pk, 5)

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

        POST_data['form-0-DELETE'] = 'yes'
        POST_data['form-1-DELETE'] = 'yes'
        POST_data['form-2-DELETE'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        # three categories got removed
        self.assertEqual(Category.objects.count(), 2)

        # both of the other categories got their parents reassigned to None
        self.assertEqual(Category.objects.filter(parent=None).count(),
                          2)

    def test_POST_bulk_delete(self):
        """
        A POST request to the categories view with a valid formset and a
        POST['bulk_action'] of 'delete' should reject the videos with the bulk
        option checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['form-2-BULK'] = 'yes'
        POST_data['submit'] = 'Apply'
        POST_data['bulk_action'] = 'delete'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))


        # three categories got removed
        self.assertEqual(Category.objects.count(), 2)

        # both of the other categories got their parents reassigned to None
        self.assertEqual(Category.objects.filter(parent=None).count(),
                          2)


# -----------------------------------------------------------------------------
# Bulk edit administration tests
# -----------------------------------------------------------------------------

class BulkEditVideoFormTestCase(BaseTestCase):
    fixtures = AdministrationBaseTestCase.fixtures + [
        'feeds', 'videos', 'categories']

    def _form2POST(self, form):
        POST_data = {}
        for name, field in form.fields.items():
            data = form.initial.get(name, field.initial)
            if callable(data):
                data = data()
            if isinstance(data, (list, tuple)):
                data = [force_unicode(item) for item in data]
            elif data:
                data = force_unicode(data)
            if data:
                POST_data[form.add_prefix(name)] = data
        return POST_data

    @mock.patch('localtv.models.Video.save_thumbnail')
    def test_save_thumbnail_false(self, mock_save_thumbnail):
        vid = Video.objects.exclude(thumbnail_url='')[0]
        import localtv.admin.forms
        data = self._form2POST(localtv.admin.forms.EditVideoForm(instance=vid))
        form = localtv.admin.forms.EditVideoForm(data, instance=vid)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertFalse(mock_save_thumbnail.called)

    @mock.patch('localtv.models.Video.save_thumbnail')
    def test_save_thumbnail_true(self, mock_save_thumbnail):
        vid = Video.objects.exclude(thumbnail_url='')[0]
        import localtv.admin.forms
        data = self._form2POST(localtv.admin.forms.EditVideoForm(instance=vid))
        data['thumbnail_url'] = 'http://www.google.com/logos/2011/persiannewyear11-hp.jpg'
        form = localtv.admin.forms.EditVideoForm(data, instance=vid)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(mock_save_thumbnail.called)

    def test_index_after_m2m(self):
        """
        After the videos are saved, their indexed equivalents should have the
        same authors and categories that they have.

        """
        from localtv.admin.forms import BulkEditVideoForm
        instance = Video.objects.filter(status=Video.ACTIVE)[0]
        result = SearchQuerySet().filter(django_id=instance.pk)[0]

        self.assertEqual([unicode(pk) for pk in result.categories],
                         [unicode(pk) for pk in
                          instance.categories.values_list('pk', flat=True)])
        self.assertEqual([unicode(pk) for pk in result.authors],
                         [unicode(pk) for pk in
                          instance.authors.values_list('pk', flat=True)])

        data = model_to_dict(instance)
        data.update({
            'categories': list(Category.objects.values_list('pk', flat=True)),
            'authors': list(User.objects.values_list('pk', flat=True)),
        })

        form = BulkEditVideoForm(data=data, instance=instance)

        self.assertTrue(form.is_valid())
        instance = form.save()
        result = SearchQuerySet().filter(django_id=instance.pk)[0]

        self.assertEqual(list(instance.categories.all()),
                         list(Category.objects.all()))
        self.assertEqual(list(instance.authors.all()),
                         list(User.objects.all()))
        self.assertEqual(set([unicode(pk) for pk in result.categories]),
                         set([unicode(pk) for pk in
                              Category.objects.values_list('pk', flat=True)]))
        self.assertEqual(set([unicode(pk) for pk in result.authors]),
                         set([unicode(pk) for pk in
                              User.objects.values_list('pk', flat=True)]))


class BulkEditAdministrationTestCase(AdministrationBaseTestCase):
    fixtures = AdministrationBaseTestCase.fixtures + [
        'feeds', 'videos', 'categories']

    url = reverse_lazy('localtv_admin_bulk_edit')

    @staticmethod
    def Video_sort_lower(*args, **kwargs):
        videos = Video.objects.all()
        if args or kwargs:
            videos = videos.filter(*args, **kwargs)
        return videos.extra(select={
                'name_lower': 'LOWER(localtv_video.name)'}).order_by(
            'name_lower')

    def test_GET(self):
        """
        A GET request to the bulk_edit view should return a paged view of the
        videos, sorted in alphabetical order.  It should render the
        'localtv/admin/bulk_edit.html' template.

        Context:

        * formset: the FormSet for the videos on the current page
        * page: the Page object for the current page
        * headers: the headers for the table
        * categories: a QuerySet for the categories of the site
        * users: a Queryset for the users on the site
        """
        # Add tags to a video
        video = self.Video_sort_lower(status=Video.ACTIVE)[0];
        video.tags = 'SomeSpecificTagString AnotherSpecificTagString'
        video.save()
        
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)

        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/bulk_edit.html')
        self.assertEqual(response.context[0]['page'].number, 1)
        self.assertTrue('formset' in response.context[0])
        self.assertEqual(
            [form.instance for form in
             response.context[0]['formset'].initial_forms],
            list(
                self.Video_sort_lower(status=Video.ACTIVE)[:50]))
        self.assertEqual(
            [form.initial['tags'] for form in
             response.context[0]['formset'].initial_forms],
            list (utils.edit_string_for_tags(video.tags) for video in
                  self.Video_sort_lower(status=Video.ACTIVE)[:50]))
        self.assertTrue('headers' in response.context[0])
        self.assertEqual(list(response.context[0]['categories']),
                          list(Category.objects.filter(
                site=self.site_settings.site)))
        self.assertEqual(list(response.context[0]['users']),
                          list(User.objects.order_by('username')))

    def test_GET_sorting(self):
        """
        A GET request with a 'sort' key in the GET request should sort the
        sources by that field.  The default sort should be by the name of the
        video.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
                                      key=lambda x:unicode(x).lower())),
                          list(page.object_list))

        # reversed name
        response = c.get(self.url, {'sort': '-name'})
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:unicode(x).lower())),
                          list(page.object_list))

        # auto approve
        response = c.get(self.url, {'sort': 'when_published'})
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
                                      key=lambda x:x.when_published)),
                          list(page.object_list))

        # reversed auto_approve
        response = c.get(self.url, {'sort': '-when_published'})
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:x.when_published)),
                          list(page.object_list))

        # source (feed, search, user)
        response = c.get(self.url, {'sort': 'source'})
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
                                      key=lambda x:x.source_type())),
                          list(page.object_list))

        # reversed source (user, search, feed)
        response = c.get(self.url, {'sort': '-source'})
        page = response.context['page']
        self.assertEqual(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:x.source_type())),
                          list(page.object_list))

    def test_GET_filter_categories(self):
        """
        A GET request with a 'category' key in the GET request should filter
        the results to only include videos from that category.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'category': '3'})
        self.assertEqual(list(response.context['page'].object_list),
                          list(self.Video_sort_lower(
                    categories=3,
                    status=Video.ACTIVE,
                    )))

    def test_GET_filter_authors(self):
        """
        A GET request with an 'author' key in the GET request should filter the
        results to only include videos with that author.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'author': '3'})
        self.assertEqual(list(response.context['page'].object_list),
                          list(self.Video_sort_lower(
                    authors=3,
                    status=Video.ACTIVE,
                    )))

    def test_GET_filter_featured(self):
        """
        A GET request with a GET['filter'] of 'featured' should restrict the
        results to only those videos that have been featured.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'filter': 'featured'})
        self.assertEqual(list(response.context['page'].object_list),
                          list(self.Video_sort_lower(
                    status=Video.ACTIVE,
                    ).exclude(last_featured=None)))

    def test_GET_filter_no_attribution(self):
        """
        A GET request with a GET['filter'] of 'no-attribution' should restrict
        the results to only those videos that have do not have an authors
        assigned.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'filter': 'no-attribution'})
        self.assertEqual(list(response.context['page'].object_list),
                          list(self.Video_sort_lower(
                    status=Video.ACTIVE,
                    authors=None)))

    def test_GET_filter_no_category(self):
        """
        A GET request with a GET['filter'] of 'no-category' should restrict the
        results to only those videos that do not have a category assigned.
        """
        # the first page of videos all don't have categories, so we give them
        # some so that there's something to filter
        for video in Video.objects.order_by('name')[:20]:
            video.categories = [1]
            video.save()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'filter': 'no-category'})
        self.assertEqual(list(response.context['page'].object_list),
                          list(self.Video_sort_lower(
                    status=Video.ACTIVE,
                    categories=None)))

    def test_GET_filter_rejected(self):
        """
        A GET request with a GET['filter'] of 'rejected' should restrict the
        results to only those videos that have been rejected.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'filter': 'rejected'})
        self.assertEqual(list(response.context['page'].object_list),
                          list(self.Video_sort_lower(
                    status=Video.REJECTED)))

    def test_GET_search(self):
        """
        A GET request with a 'q' key in the GET request should search the
        videos for that string.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'q': 'blend'})
        self.assertEqual(list(response.context['page'].object_list),
                          list(self.Video_sort_lower(
                    Q(name__icontains="blend") |
                    Q(description__icontains="blend") |
                    Q(feed__name__icontains="blend"),
                    status=Video.ACTIVE,
                    )))

    def test_POST_failure(self):
        """
        A POST request to the bulk_edit view with an invalid formset
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
        del POST_data_invalid['form-1-name']

        POST_response = c.post(self.url, POST_data_invalid)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertTrue(POST_response.context['formset'].is_bound)
        self.assertFalse(POST_response.context['formset'].is_valid())
        self.assertEqual(len(POST_response.context['formset'].errors[0]), 1)
        self.assertEqual(len(POST_response.context['formset'].errors[1]), 1)

        # make sure the data hasn't changed
        self.assertEqual(POST_data,
                          self._POST_data_from_formset(
                POST_response.context['formset']))

    def test_POST_succeed(self):
        """
        A POST request to the bulk_edit view with a valid formset should
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
                'form-0-file_url': 'http://pculture.org/',
                'form-0-tags': 'tag1 tag2',
                'form-1-description': 'localtv',
                'form-1-embed_code': 'new embed code',
                'form-1-tags': 'tag3 tag4',
                })

        POST_response = c.post(self.url, POST_data,
                               follow=True)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEqual(POST_response.redirect_chain,
                          [('http://%s%s?successful' % (
                        'testserver',
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

        # make sure the data has been updated
        video1 = Video.objects.get(pk=POST_data['form-0-id'])
        self.assertEqual(video1.name, POST_data['form-0-name'])
        self.assertEqual(video1.file_url, POST_data['form-0-file_url'])
        self.assertEqual(video1.embed_code, POST_data['form-0-embed_code'])
        self.assertEqual(set(video1.tags.values_list('name', flat=True)),
                          set(['tag1', 'tag2']))

        video2 = Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertEqual(video2.description,
                          POST_data['form-1-description'])
        self.assertEqual(video2.embed_code,
                          POST_data['form-1-embed_code'])
        self.assertEqual(set(video2.tags.values_list('name', flat=True)),
                          set(['tag3', 'tag4']))

    def test_POST_change_just_one_video(self):
        """
        Here, we POST to the bulk edit view with a valid
        formset, and we change the name of just one video
        using its particular form.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data.update({
                'form-11-description': 'new description',
                })


        POST_response = c.post(self.url, POST_data,
                               follow=True)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEqual(POST_response.redirect_chain,
                          [('http://%s%s?successful' % (
                        'testserver',
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

        # make sure the data has been updated
        video = Video.objects.get(
            pk=POST_data['form-11-id'])
        self.assertEqual(video.description,
                          POST_data['form-11-description'])

    def test_POST_change_just_one_video_without_authors(self):
        """
        Here, we POST to the bulk edit view with a valid
        formset, and we change the name of just one video
        using its particular form.

        This time we fail to submit any author data. We want to
        make sure that the video still has the same authors list.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        original_POST_data = self._POST_data_from_formset(formset)

        POST_data = original_POST_data.copy()
        del POST_data['form-11-authors']

        POST_response = c.post(self.url, POST_data,
                               follow=True)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEqual(POST_response.redirect_chain,
                          [('http://%s%s?successful' % (
                        'testserver',
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

        # make sure the data remains the same: in the form...
        video = Video.objects.get(
            pk=POST_data['form-11-id'])
        self.assertEqual([unicode(x.id) for x in video.authors.all()],
                          original_POST_data['form-11-authors'])

        # ...in the database
        self.assertEqual([3],
                         [x.id for x in video.authors.all()])

    def test_POST_change_just_one_video_actually_change_authors(self):
        """
        Here, we POST to the bulk edit view with a valid
        formset, and we change the name of just one video
        using its particular form.

        This time we fail to submit any author data. We also remove
        the skip_authors field, which means that the form
        should process this change.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        original_POST_data = self._POST_data_from_formset(formset)

        POST_data = original_POST_data.copy()
        del POST_data['form-11-skip_authors']
        del POST_data['form-11-authors']

        POST_response = c.post(self.url, POST_data,
                               follow=True)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEqual(POST_response.redirect_chain,
                          [('http://%s%s?successful' % (
                        'testserver',
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

        # make sure the data has changed in the DB
        video = Video.objects.get(
            pk=POST_data['form-11-id'])
        self.assertEqual([],
                         [x.id for x in video.authors.all()])

    def test_POST_succeed_with_page(self):
        """
        A POST request to the bulk_edit view with a valid formset should
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
        self.assertEqual(POST_response.redirect_chain,
                          [('http://%s%s?page=2&successful' % (
                        'testserver',
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

    def test_POST_succeed_with_existing_successful(self):
        """
        A POST request to the bulk_edit view with a valid formset should save
        the updated models and redirect to the same URL if 'successful' is
        already in the GET arguments.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'page': 2})
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_response = c.post(self.url+"?page=2&successful", POST_data,
                               follow=True)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEqual(POST_response.redirect_chain,
                          [('http://%s%s?page=2&successful' % (
                        'testserver',
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

    def test_POST_delete(self):
        """
        A POST request to the bulk_edit view with a valid formset and a
        DELETE value for a source should reject that video.`
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)
        POST_data['form-0-DELETE'] = 'yes'
        POST_data['form-1-DELETE'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        # make sure the data has been updated
        video1 = Video.objects.get(pk=POST_data['form-0-id'])
        self.assertEqual(video1.status, Video.REJECTED)

        video2 = Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertEqual(video2.status, Video.REJECTED),

    def test_POST_bulk_edit(self):
        """
        A POST request to the bulk_edit view with a valid formset and the
        extra form filled out should update any source with the bulk option
        checked.
        """
        # give the first video a category
        video = Video.objects.filter(status=Video.ACTIVE).order_by('name')[0]
        video.categories =[Category.objects.get(pk=2)]
        video.save()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)
        index = len(formset.forms) - 1
        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['form-%i-name' % index] = 'New Name'
        POST_data['form-%i-description' % index] = 'New Description'
        POST_data['form-%i-when_published' % index] = datetime.datetime(
            1985, 3, 24, 18, 55, 00)
        POST_data['form-%i-categories' % index] = [1]
        POST_data['form-%i-authors' % index] = [1, 2]
        POST_data['form-%i-tags' % index] = 'tag3, tag4'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        # make sure the data has been updated
        video1 = Video.objects.get(pk=POST_data['form-0-id'])
        video2 = Video.objects.get(
            pk=POST_data['form-1-id'])

        self.assertEqual(
            set(video1.categories.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEqual(
            set(video2.categories.values_list('pk', flat=True)),
            set([1]))

        for video in video1, video2:
            self.assertEqual(video.name, 'New Name')
            self.assertEqual(video.description, 'New Description')
            self.assertEqual(video.when_published,
                              datetime.datetime(1985, 3, 24,
                                                18, 55, 00))
            self.assertEqual(
                set(video.authors.values_list('pk', flat=True)),
                set([1, 2]))
            self.assertEqual(set(video.tags.values_list('name', flat=True)),
                                  set(['tag3', 'tag4']))

    def test_POST_bulk_edit_no_authors(self):
        """
        A POST request to the bulk_edit view with a valid formset and the
        extra form filled out should update any source with the bulk option
        checked.
        """
        # give the first video a category
        video = Video.objects.filter(status=Video.ACTIVE).order_by('name')[0]
        video.categories =[Category.objects.get(pk=2)]
        video.save()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)
        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['form-%i-categories' % (len(formset.forms) - 1)] = [1]
        POST_data['form-%i-tags' % (len(formset.forms) - 1)] = 'tag3, tag4'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        # make sure the data has been updated
        video1 = Video.objects.get(pk=POST_data['form-0-id'])
        video2 = Video.objects.get(
            pk=POST_data['form-1-id'])

        self.assertEqual(
            set(video1.categories.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEqual(
            set(video2.categories.values_list('pk', flat=True)),
            set([1]))

        for video in video1, video2:
            self.assertEqual(
                set(video.authors.values_list('pk', flat=True)), set())
            self.assertEqual(set(video.tags.values_list('name', flat=True)),
                                  set(['tag3', 'tag4']))

    def test_POST_bulk_delete(self):
        """
        A POST request to the bulk_edit view with a valid formset and a
        POST['bulk_action'] of 'delete' should reject the videos with the bulk
        option checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['bulk_action'] = 'delete'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        # make sure the data has been updated
        video1 = Video.objects.get(pk=POST_data['form-0-id'])
        self.assertEqual(video1.status, Video.REJECTED)

        video2 = Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertEqual(video2.status, Video.REJECTED)

    def test_POST_bulk_unapprove(self):
        """
        A POST request to the bulk_edit view with a valid formset and a
        POST['bulk_action'] of 'unapprove' should unapprove the videos with the
        bulk option checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['bulk_action'] = 'unapprove'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        # make sure the data has been updated
        video1 = Video.objects.get(pk=POST_data['form-0-id'])
        self.assertEqual(video1.status, Video.UNAPPROVED)

        video2 = Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertEqual(video2.status, Video.UNAPPROVED)

    def test_POST_bulk_feature(self):
        """
        A POST request to the bulk_edit view with a valid formset and a
        POST['bulk_action'] of 'feature' should feature the videos with the
        bulk option checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['bulk_action'] = 'feature'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        # make sure the data has been updated
        video1 = Video.objects.get(pk=POST_data['form-0-id'])
        self.assertTrue(video1.last_featured is not None)

        video2 = Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertTrue(video2.last_featured is not None)

    def test_POST_bulk_unfeature(self):
        """
        A POST request to the bulk_edit view with a valid formset and a
        POST['bulk_action'] of 'feature' should feature the videos with the
        bulk option checked.
        """
        for v in Video.objects.all():
            v.last_featured = datetime.datetime.now()
            v.save()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['bulk_action'] = 'unfeature'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        # make sure the data has been updated
        video1 = Video.objects.get(pk=POST_data['form-0-id'])
        self.assertTrue(video1.last_featured is None)

        video2 = Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertTrue(video2.last_featured is None)


# -----------------------------------------------------------------------------
# Design administration tests
# -----------------------------------------------------------------------------


class EditSettingsAdministrationTestCase(AdministrationBaseTestCase):

    url = reverse_lazy('localtv_admin_settings')

    def setUp(self):
        AdministrationBaseTestCase.setUp(self)
        self.POST_data = {
            'title': self.site_settings.site.name,
            'tagline': self.site_settings.tagline,
            'about_html': self.site_settings.about_html,
            'sidebar_html': self.site_settings.sidebar_html,
            'footer_html': self.site_settings.footer_html,
            'css': self.site_settings.css}

    def test_GET(self):
        """
        A GET request to the edit_settings view should render the
        'localtv/admin/edit_settings.html' template and include a form.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/edit_settings.html')
        self.assertTrue('form' in response.context[0])

    def test_POST_title_failure(self):
        """
        A POST request to the edit_settings view with an invalid form
        should rerender the template and include the form errors.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data['title'] = ''
        POST_response = c.post(self.url, )

        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEqual(POST_response.templates[0].name,
                          'localtv/admin/edit_settings.html')
        self.assertFalse(POST_response.context['form'].is_valid())

    def test_POST_title_long_title(self):
        """
        A POST request to the edit design view with a long (>50 character)
        title should give a form error, not a 500 error.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data['title'] = 'New Title' * 10

        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEqual(POST_response.templates[0].name,
                          'localtv/admin/edit_settings.html')
        self.assertFalse(POST_response.context['form'].is_valid())

    def test_POST_succeed(self):
        """
        A POST request to the edit_settings view with a valid form should save
        the data and redirect back to the edit_settings view.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data.update({
                'title': 'New Title',
                'tagline': 'New Tagline',
                'about_html': 'New About',
                'sidebar_html': 'New Sidebar',
                'footer_html': 'New Footer',
                'logo': file(self._data_file('logo.png')),
                'background': file(self._data_file('logo.png')),
                'display_submit_button': 'yes',
                'submission_requires_login': 'yes',
                'use_original_date': '',
                'css': 'New Css',
                'screen_all_comments': 'yes',
                'comments_required_login': 'yes'})

        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        site_settings = SiteSettings.objects.get(
            pk=self.site_settings.pk)
        self.assertEqual(site_settings.site.name, 'New Title')
        self.assertEqual(site_settings.tagline, 'New Tagline')
        self.assertEqual(site_settings.about_html, 'New About')
        self.assertEqual(site_settings.sidebar_html, 'New Sidebar')
        self.assertEqual(site_settings.footer_html, 'New Footer')
        self.assertEqual(site_settings.css, 'New Css')
        self.assertTrue(site_settings.display_submit_button)
        self.assertTrue(site_settings.submission_requires_login)
        self.assertFalse(site_settings.use_original_date)
        self.assertTrue(site_settings.screen_all_comments)
        self.assertTrue(site_settings.comments_required_login)

        logo_data = file(self._data_file('logo.png')).read()
        site_settings.logo.open()
        self.assertEqual(site_settings.logo.read(), logo_data)
        site_settings.background.open()
        self.assertEqual(site_settings.background.read(), logo_data)

    def test_POST_logo_background_long_name(self):
        """
        If the logo or background images have a long name, they should be
        chopped off at 25 characters.
        """
        name = 'x' * 200 + '.png'
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data.update({
                'logo': File(file(self._data_file('logo.png')), name),
                'background': File(file(self._data_file('logo.png')), name)
                })
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        site_settings = SiteSettings.objects.get(
            pk=self.site_settings.pk)
        logo_data = file(self._data_file('logo.png')).read()
        site_settings.logo.open()
        self.assertEqual(site_settings.logo.read(), logo_data)
        site_settings.background.open()
        self.assertEqual(site_settings.background.read(), logo_data)

        logo_name = site_settings.logo.name
        background_name = site_settings.background.name
        # don't send them again, and make sure the names stay the same
        del self.POST_data['logo']
        del self.POST_data['background']

        POST_response = c.post(self.url, self.POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        site_settings = SiteSettings.objects.get(
            pk=self.site_settings.pk)
        self.assertEqual(site_settings.logo.name, logo_name)
        self.assertEqual(site_settings.background.name,
                          background_name)

    def test_POST_delete_background(self):
        """
        A POST request to the edit_content view with POST['delete_background']
        should remove the background image and redirect back to the edit
        design view.
        """
        self.site_settings.background = File(file(self._data_file('logo.png')))
        self.site_settings.save()

        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data['delete_background'] = 'yes'
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        site_settings = SiteSettings.objects.get(
            pk=self.site_settings.pk)
        self.assertEqual(site_settings.background, '')

    def test_POST_delete_background_missing(self):
        """
        A POST request to the edit_content view with POST['delete_background']
        but no background just redirect back to the edit
        design view.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data['delete_background'] = 'yes'
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        site_settings = SiteSettings.objects.get(
            pk=self.site_settings.pk)
        self.assertEqual(site_settings.background, '')


# -----------------------------------------------------------------------------
# Flatpage administration tests
# -----------------------------------------------------------------------------


class FlatPageAdministrationTestCase(AdministrationBaseTestCase):

    fixtures = AdministrationBaseTestCase.fixtures + [
        'flatpages']

    url = reverse_lazy('localtv_admin_flatpages')

    def test_GET(self):
        """
        A GET request to the flatpage view should render the
        'localtv/admin/flatpages.html' template and include a formset
        for the flatpages and a form to add a new page.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/flatpages.html')
        self.assertTrue('formset' in response.context[0])
        self.assertTrue('form' in response.context[0])

    def test_POST_add_failure(self):
        """
        A POST to the flatpages view with a POST['submit'] value of 'Add' but
        a failing form should rerender the template.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url,
                          {'submit': 'Add'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/flatpages.html')
        self.assertTrue('formset' in response.context[0])
        self.assertTrue(
            getattr(response.context[0]['form'],
                    'errors') is not None)

    def test_POST_save_failure(self):
        """
        A POST to the flatpages view with a POST['submit'] value of 'Save' but
        a failing formset should rerender the template.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/flatpages.html')
        self.assertTrue(
            getattr(response.context[0]['formset'], 'errors') is not None)
        self.assertTrue('form' in response.context[0])

    def test_POST_add(self):
        """
        A POST to the flatpages view with a POST['submit'] of 'Add' and a
        successful form should create a new category and redirect the user back
        to the management page.
        """
        c = Client()
        c.login(username="admin", password="admin")
        POST_data = {
            'submit': 'Add',
            'title': 'new flatpage',
            'url': '/flatpage/',
            'content': 'flatpage content',
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        new = FlatPage.objects.order_by('-id')[0]

        self.assertEqual(list(new.sites.all()), [self.site_settings.site])

        for key, value in POST_data.items():
            if key == 'submit':
                pass
            else:
                self.assertEqual(getattr(new, key), value)

    def test_POST_add_existing_flatpage(self):
        """
        The admin should not be able to add a flatpage representing an existing
        flatpage.
        """
        c = Client()
        c.login(username="admin", password="admin")
        POST_data = {
            'submit': 'Add',
            'title': 'flatpage',
            'url': '/flatpage0/',
            'content': 'flatpage content',
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/flatpages.html')
        self.assertTrue('formset' in response.context[0])
        self.assertTrue(
            getattr(response.context[0]['form'],
                    'errors') is not None)

    def test_POST_add_existing_view(self):
        """
        The admin should not be able to add a flatpage representing an existing
        view.
        """
        c = Client()
        c.login(username="admin", password="admin")
        POST_data = {
            'submit': 'Add',
            'title': 'flatpage',
            'url': self.url,
            'content': 'flatpage content',
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/admin/flatpages.html')
        self.assertTrue('formset' in response.context[0])
        self.assertTrue(
            getattr(response.context[0]['form'],
                    'errors') is not None)

    def test_POST_save_no_changes(self):
        """
        A POST to the flatpagess view with a POST['submit'] of 'Save' and a
        successful formset should update the category data.  The default values
        of the formset should not change the values of any of the Categorys.
        """
        c = Client()
        c.login(username="admin", password="admin")

        old_flatpages = FlatPage.objects.values()

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']

        POST_response = c.post(self.url, self._POST_data_from_formset(
                formset,
                submit='Save'))

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        for old, new in zip(old_flatpages, FlatPage.objects.values()):
            self.assertEqual(old, new)

    def test_POST_save_changes(self):
        """
        A POST to the flatpages view with a POST['submit'] of 'Save' and a
        successful formset should update the category data.
        """
        c = Client()
        c.login(username="admin", password="admin")

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']
        POST_data = self._POST_data_from_formset(formset,
                                                 submit='Save')


        POST_data['form-0-title'] = 'New Title'
        POST_data['form-0-url'] = '/newflatpage/'
        POST_data['form-1-content'] = 'New Content'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        self.assertEqual(FlatPage.objects.count(), 5) # no one got added

        new_url = FlatPage.objects.get(url='/newflatpage/')
        self.assertEqual(new_url.pk, 1)
        self.assertEqual(new_url.title, 'New Title')

        new_content = FlatPage.objects.get(url='/flatpage1/')
        self.assertEqual(new_content.content, 'New Content')

    def test_POST_delete(self):
        """
        A POST to the flatpages view with a POST['submit'] of 'Save' and a
        successful formset should update the flatpages data.  If form-*-DELETE
        is present, that page should be removed.
        """
        c = Client()
        c.login(username="admin", password="admin")

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']
        POST_data = self._POST_data_from_formset(formset,
                                                 submit='Save')

        POST_data['form-0-DELETE'] = 'yes'
        POST_data['form-1-DELETE'] = 'yes'
        POST_data['form-2-DELETE'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))

        # three flatpages got removed
        self.assertEqual(FlatPage.objects.count(), 2)

    def test_POST_bulk_delete(self):
        """
        A POST request to the flatpages view with a valid formset and a
        POST['bulk_action'] of 'delete' should reject the videos with the bulk
        option checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-BULK'] = 'yes'
        POST_data['form-1-BULK'] = 'yes'
        POST_data['form-2-BULK'] = 'yes'
        POST_data['submit'] = 'Apply'
        POST_data['bulk_action'] = 'delete'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s?successful' % (
                'testserver',
                self.url))


        # three flatpages got removed
        self.assertEqual(FlatPage.objects.count(), 2)


class AdminDashboardLoadsWithoutError(BaseTestCase):
    url = reverse_lazy('localtv_admin_index')

    def test(self):
        """
        This view should have status code 200 for an admin.

        (This is there to make sure we at least *cover* the index view.)
        """
        self.assertRequiresAuthentication(self.url)

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
