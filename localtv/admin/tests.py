# This file is part of Miro Community.
# Copyright (C) 2009, 2010, 2011 Participatory Culture Foundation
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

class Fakedatetime(datetime.datetime):
    @classmethod
    def utcnow(cls):
        return cls(2011, 2, 20, 12, 35, 0)

from django.core.files.base import File
from django.core.paginator import Page
from django.core import mail
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.db.models import Q
from django.test.client import Client
from django.utils.encoding import force_unicode
from django.conf import settings
import mock
from notification import models as notification
from tagging.utils import edit_string_for_tags
from uploadtemplate.models import Theme
import vidscraper

from localtv import utils
import localtv.management.commands.check_frequently_for_invalid_tiers_state
from localtv.models import Feed, Video, SavedSearch, Category, SiteLocation, TierInfo
from localtv.tests import BaseTestCase
import localtv.tiers

Profile = utils.get_profile_model()

NAME_TO_COST = localtv.tiers.Tier.NAME_TO_COST()
PLUS_COST = NAME_TO_COST['plus']
PREMIUM_COST = NAME_TO_COST['premium']
MAX_COST = NAME_TO_COST['max']

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

    fixtures = BaseTestCase.fixtures + ['videos', 'feeds', 'savedsearches']

    url = reverse('localtv_admin_approve_reject')

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
        self.assertEqual(response.template[0].name,
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
        unapproved_videos = Video.objects.unapproved().order_by(
            'when_submitted', 'when_published')
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
        video = Video.objects.unapproved()[0]
        url = reverse('localtv_admin_preview_video')
        self.assertRequiresAuthentication(url, {'video_id': str(video.pk)})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url,
                         {'video_id': str(video.pk)})
        self.assertEqual(response.template[0].name,
                          'localtv/admin/video_preview.html')
        self.assertEqual(response.context['current_video'],
                          video)

    def test_GET_approve(self):
        """
        A GET request to the approve_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].
        """
        video = Video.objects.unapproved()[0]
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

    @mock.patch('localtv.tiers.Tier.videos_limit', mock.Mock(return_value=2))
    def test_GET_approve_fails_when_over_limit(self):
        """
        A GET request to the approve_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].
        """
        video = Video.objects.unapproved()[0]
        url = reverse('localtv_admin_approve_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 402)

    def test_GET_approve_email(self):
        """
        If the video is approved, and the submitter has the 'video_approved'
        notification on, they should receive an e-mail notifying them of it.
        """
        video = Video.objects.unapproved()[0]
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
        video = Video.objects.unapproved()[0]
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
        video = Video.objects.unapproved()[0]
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
        video = Video.objects.unapproved()[0]
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

    @mock.patch('localtv.tiers.Tier.videos_limit', mock.Mock(return_value=2))
    def test_GET_feature_fails_outside_video_limit(self):
        """
        A GET request to the feature_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].  If the video is unapproved, it should become
        approved.
        """
        video = Video.objects.unapproved()[0]
        url = reverse('localtv_admin_feature_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 402)

    def test_GET_unfeature(self):
        """
        A GET request to the unfeature_video view should unfeature the video
        and redirect back to the referrer.  The video should be specified by
        GET['video_id'].  The video status is not affected.
        """
        video = Video.objects.active().exclude(
            last_featured=None)[0]

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
        unapproved_videos = Video.objects.unapproved()
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
        unapproved_videos = Video.objects.unapproved()
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
        unapproved_videos = Video.objects.unapproved()
        unapproved_videos_count = unapproved_videos.count()

        url = reverse('localtv_admin_clear_all')
        self.assertRequiresAuthentication(url)

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/admin/clear_confirm.html')
        self.assertEqual(list(response.context['videos']),
                          list(unapproved_videos))

        # nothing was rejected
        self.assertEqual(Video.objects.unapproved().count(),
                          unapproved_videos_count)

    def test_POST_clear_all_failure(self):
        """
        A POST request to the clear_all view without POST['confirm'] = 'yes'
        should render the 'localtv/admin/clear_confirm.html' template
        and have a 'videos' variable in the context which is a list of all the
        unapproved videos.
        """
        unapproved_videos = Video.objects.unapproved()
        unapproved_videos_count = unapproved_videos.count()

        url = reverse('localtv_admin_clear_all')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/admin/clear_confirm.html')
        self.assertEqual(list(response.context['videos']),
                          list(unapproved_videos))

        # nothing was rejected
        self.assertEqual(Video.objects.unapproved().count(),
                          unapproved_videos_count)

    def test_POST_clear_all_succeed(self):
        """
        A POST request to the clear_all view with POST['confirm'] = 'yes'
        should reject all the videos and redirect to the approve_reject view.
        """
        unapproved_videos = Video.objects.unapproved()
        unapproved_videos_count = unapproved_videos.count()

        rejected_videos = Video.objects.rejected()
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
        self.assertEqual(Video.objects.rejected().count(),
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
        self.assertEqual(response.template[0].name,
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

    url = reverse('localtv_admin_feed_add')
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
        self.assertEqual(response.template[0].name,
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
            site=self.site_location.site,
            last_updated=datetime.datetime.now(),
            status=Feed.UNAPPROVED,
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
            site=self.site_location.site,
            last_updated=datetime.datetime.now(),
            status=Feed.UNAPPROVED,
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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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
                           'auto_approve': 'yes',
                           'avoid_frontpage': 'on'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'],
                          'http://%s%s' % (
                'testserver',
                reverse('localtv_admin_manage_page')))

        feed = Feed.objects.get()
        self.assertEqual(feed.name, 'Valid Feed with Relative Links')
        self.assertEqual(feed.feed_url, self.feed_url)
        # if CELERY_ALWAYS_EAGER is True, we'll have imported the feed here
        self.assertTrue(feed.status in (Feed.UNAPPROVED, Feed.ACTIVE))
        self.assertEqual(feed.avoid_frontpage, True)
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
                          'http://www.youtube.com/profile?'
                          'user=mphtower#p/u')
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
        feed = Feed.objects.create(site=self.site_location.site,
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
        feed = Feed.objects.create(site=self.site_location.site,
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

    url = reverse('localtv_admin_search')

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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response2.context[2]['page_obj'].number, 2)
        self.assertEqual(len(response2.context[2]['page_obj'].object_list),
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
        self.assertEqual(v.site, self.site_location.site)
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

    @mock.patch('localtv.tiers.Tier.can_add_more_videos', mock.Mock(return_value=False))
    def test_GET_approve_refuses_when_limit_exceeded(self):
        """
        A GET request to the approve view should create a new video object from
        the search and redirect back to the referrer.  The video should be
        removed from subsequent search listings.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'q': 'search string'})
        metasearch_video = response.context[2]['page_obj'].object_list[0]
        metasearch_video2 = response.context[2]['page_obj'].object_list[1]

        response = c.get(reverse('localtv_admin_search_video_approve'),
                         {'q': 'search string',
                          'video_id': metasearch_video.id},
                         HTTP_REFERER="http://www.getmiro.com/")
        self.assertStatusCodeEquals(response, 402)

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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(saved_search.site, self.site_location.site)
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
            site=self.site_location.site,
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
        self.assertEqual(response['Location'],
                          'http://www.getmiro.com/')

        saved_search = SavedSearch.objects.get(pk=saved_search.pk)
        self.assertFalse(saved_search.auto_approve)

# -----------------------------------------------------------------------------
# User administration tests
# -----------------------------------------------------------------------------


class UserAdministrationTestCase(AdministrationBaseTestCase):

    url = reverse('localtv_admin_users')

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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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
                new_site_location = SiteLocation.objects.get()
                self.assertFalse(new_site_location.user_is_admin(new))
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
                new_site_location = SiteLocation.objects.get()
                self.assertTrue(new_site_location.user_is_admin(new))
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
        self.assertTrue(self.site_location.user_is_admin(new_admin))
        self.assertTrue(new_admin.check_password('new_admin'))
        self.assertEqual(new_admin.get_profile().location, 'New Location')

        superuser = User.objects.get(username='superuser')
        self.assertEqual(superuser.pk, 2)
        self.assertEqual(superuser.is_superuser, True)
        self.assertEqual(superuser.first_name, '')
        self.assertEqual(superuser.last_name, '')
        self.assertFalse(superuser in self.site_location.admins.all())
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
        self.assertFalse(self.site_location.user_is_admin(old_admin))
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

    url = reverse('localtv_admin_categories')

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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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

        self.assertEqual(new.site, self.site_location.site)

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

class BulkEditAdministrationTestCase(AdministrationBaseTestCase):
    fixtures = AdministrationBaseTestCase.fixtures + [
        'feeds', 'videos', 'categories']

    url = reverse('localtv_admin_bulk_edit')

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
        self.assertEqual(response.template[0].name,
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
            list (edit_string_for_tags(video.tags) for video in
                  self.Video_sort_lower(status=Video.ACTIVE)[:50]))
        self.assertTrue('headers' in response.context[0])
        self.assertEqual(list(response.context[0]['categories']),
                          list(Category.objects.filter(
                site=self.site_location.site)))
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
        video = Video.objects.active().order_by('name')[0]
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
        video = Video.objects.active().order_by('name')[0]
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

# ----------------------------------
# Administration tests with tiers
# ----------------------------------

def naysayer(*args, **kwargs):
    return False

class EditSettingsDeniedSometimesTestCase(AdministrationBaseTestCase):

    url = reverse('localtv_admin_settings')

    def setUp(self):
        AdministrationBaseTestCase.setUp(self)
        self.POST_data = {
            'title': self.site_location.site.name,
            'tagline': self.site_location.tagline,
            'about_html': self.site_location.about_html,
            'sidebar_html': self.site_location.sidebar_html,
            'footer_html': self.site_location.footer_html,
            'css': self.site_location.css}

    @mock.patch('localtv.tiers.Tier.permit_custom_css', naysayer)
    def test_POST_css_failure(self):
        """
        When CSS is not permitted, the POST should fail with a validation error.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data['css'] = 'new css'
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEqual(POST_response.template[0].name,
                          'localtv/admin/edit_settings.html')
        self.assertFalse(POST_response.context['form'].is_valid())

    @mock.patch('localtv.tiers.Tier.permit_custom_css', naysayer)
    def test_POST_css_succeeds_when_same_as_db_contents(self):
        """
        When CSS is not permitted, but we send the same CSS as what
        is in the database, the form should be valid.
        """
        c = Client()
        c.login(username='admin', password='admin')
        POST_response = c.post(self.url, self.POST_data)

        # We know from the HTTP 302 that it worked.
        self.assertStatusCodeEquals(POST_response, 302)

class EditUsersDeniedSometimesTestCase(AdministrationBaseTestCase):
    url = reverse('localtv_admin_users')

    def test_POST_rejects_first_admin_beyond_superuser(self):
        """
        A POST to the users view with a POST['submit'] of 'Add' and a
        successful form should create a new user and redirect the user back to
        the management page.  If the password isn't specified,
        User.has_unusable_password() should be True.
        """
        self.site_location.tier_name = 'basic'
        self.site_location.save()
        c = Client()
        c.login(username="superuser", password="superuser")
        POST_data = {
            'submit': 'Add',
            'username': 'new',
            'email': 'new@testserver.local',
            'role': 'admin',
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 200)
        self.assertFalse(response.context['add_user_form'].is_valid())

        # but with 'premium' it works
        self.site_location.tier_name = 'premium'
        self.site_location.save()

        c = Client()
        c.login(username="admin", password="admin")
        POST_data = {
            'submit': 'Add',
            'username': 'new',
            'email': 'new@testserver.local',
            'role': 'admin',
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)

# -----------------------------------------------------------------------------
# Design administration tests
# -----------------------------------------------------------------------------


class EditSettingsAdministrationTestCase(AdministrationBaseTestCase):

    url = reverse('localtv_admin_settings')

    def setUp(self):
        AdministrationBaseTestCase.setUp(self)
        self.POST_data = {
            'title': self.site_location.site.name,
            'tagline': self.site_location.tagline,
            'about_html': self.site_location.about_html,
            'sidebar_html': self.site_location.sidebar_html,
            'footer_html': self.site_location.footer_html,
            'css': self.site_location.css}

    def test_GET(self):
        """
        A GET request to the edit_settings view should render the
        'localtv/admin/edit_settings.html' template and include a form.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(POST_response.template[0].name,
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
        self.assertEqual(POST_response.template[0].name,
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

        site_location = SiteLocation.objects.get(
            pk=self.site_location.pk)
        self.assertEqual(site_location.site.name, 'New Title')
        self.assertEqual(site_location.tagline, 'New Tagline')
        self.assertEqual(site_location.about_html, 'New About')
        self.assertEqual(site_location.sidebar_html, 'New Sidebar')
        self.assertEqual(site_location.footer_html, 'New Footer')
        self.assertEqual(site_location.css, 'New Css')
        self.assertTrue(site_location.display_submit_button)
        self.assertTrue(site_location.submission_requires_login)
        self.assertFalse(site_location.use_original_date)
        self.assertTrue(site_location.screen_all_comments)
        self.assertTrue(site_location.comments_required_login)

        logo_data = file(self._data_file('logo.png')).read()
        site_location.logo.open()
        self.assertEqual(site_location.logo.read(), logo_data)
        site_location.background.open()
        self.assertEqual(site_location.background.read(), logo_data)

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

        site_location = SiteLocation.objects.get(
            pk=self.site_location.pk)
        logo_data = file(self._data_file('logo.png')).read()
        site_location.logo.open()
        self.assertEqual(site_location.logo.read(), logo_data)
        site_location.background.open()
        self.assertEqual(site_location.background.read(), logo_data)

        logo_name = site_location.logo.name
        background_name = site_location.background.name
        # don't send them again, and make sure the names stay the same
        del self.POST_data['logo']
        del self.POST_data['background']

        POST_response = c.post(self.url, self.POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        site_location = SiteLocation.objects.get(
            pk=self.site_location.pk)
        self.assertEqual(site_location.logo.name, logo_name)
        self.assertEqual(site_location.background.name,
                          background_name)

    def test_POST_delete_background(self):
        """
        A POST request to the edit_content view with POST['delete_background']
        should remove the background image and redirect back to the edit
        design view.
        """
        self.site_location.background = File(file(self._data_file('logo.png')))
        self.site_location.save()

        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data['delete_background'] = 'yes'
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEqual(POST_response['Location'],
                          'http://%s%s' % (
                'testserver',
                self.url))

        site_location = SiteLocation.objects.get(
            pk=self.site_location.pk)
        self.assertEqual(site_location.background, '')

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

        site_location = SiteLocation.objects.get(
            pk=self.site_location.pk)
        self.assertEqual(site_location.background, '')


# -----------------------------------------------------------------------------
# Flatpage administration tests
# -----------------------------------------------------------------------------


class FlatPageAdministrationTestCase(AdministrationBaseTestCase):

    fixtures = AdministrationBaseTestCase.fixtures + [
        'flatpages']

    url = reverse('localtv_admin_flatpages')

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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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

        self.assertEqual(list(new.sites.all()), [self.site_location.site])

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
        self.assertEqual(response.template[0].name,
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
        self.assertEqual(response.template[0].name,
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

def videos_limit_of_two(*args, **kwargs):
    return 2

class CannotApproveVideoIfLimitExceeded(BaseTestCase):
    @mock.patch('localtv.tiers.Tier.videos_limit', videos_limit_of_two)
    def test_videos_over_new_limit(self):
        # Let there be one video already approved
        Video.objects.create(site_id=self.site_location.site_id, status=Video.ACTIVE)
        # Create two in the queue
        for k in range(2):
            Video.objects.create(site_id=self.site_location.site_id, status=Video.UNAPPROVED)

        first_video_id, second_video_id = [v.id for v in
                                           Video.objects.unapproved()]

        # Try to activate all of them, but that would take us over the limit.
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_admin_approve_all'),
                         {'page': '1'})
        self.assertStatusCodeEquals(response, 402)

        # Try to activate the first one -- should work fine.
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_admin_approve_video'),
                         {'video_id': str(first_video_id)})
        self.assertStatusCodeEquals(response, 200)

        # Try to activate the second one -- you're past the limit.
        # HTTP 402: Payment Required
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_admin_approve_video'),
                         {'video_id': str(second_video_id)})
        self.assertStatusCodeEquals(response, 402)

class DowngradingDisablesThings(BaseTestCase):

    @mock.patch('localtv.tiers.Tier.videos_limit', videos_limit_of_two)
    def test_videos_over_new_limit(self):
        # Create two videos
        for k in range(3):
            Video.objects.create(site_id=self.site_location.site_id, status=Video.ACTIVE)
        self.assertTrue('videos' in
                        localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))
    
    @mock.patch('localtv.tiers.Tier.videos_limit', videos_limit_of_two)
    def test_videos_within_new_limit(self):
        # Create just one video
        Video.objects.create(site_id=self.site_location.site_id)
        self.assertTrue('videos' not in
                        localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))
    
    def test_go_to_basic_from_max_warn_about_css_loss(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Delete user #2 so that we have only 1 admin, the super-user
        self.assertEqual(2, localtv.tiers.number_of_admins_including_superuser())
        User.objects.get(username='admin').delete()

        # Add some CSS to the sitelocation
        self.site_location.css = '* { display: none; }'
        self.site_location.save()

        # Go to basic, noting that we will see an 'advertising' message
        # Now, make sure that the downgrade helper notices and complains
        self.assertTrue(
            'css' in
            localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))
        
    def test_go_to_basic_from_max_skip_warn_about_css_loss(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Delete user #2 so that we have only 1 admin, the super-user
        self.assertEqual(2, localtv.tiers.number_of_admins_including_superuser())
        User.objects.get(username='admin').delete()

        # Because there is no custom CSS, a transition to 'basic' would not
        # generate a warning.

        # Go to basic, noting that we will see an 'advertising' message
        # Now, make sure that the downgrade helper notices and complains
        self.assertTrue(
            'css' not in
            localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))
        
    def test_go_to_basic_from_max_lose_advertising(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Delete user #2 so that we have only 1 admin, the super-user
        self.assertEqual(2, localtv.tiers.number_of_admins_including_superuser())
        User.objects.get(username='admin').delete()

        # Go to basic, noting that we will see an 'advertising' message
        # Now, make sure that the downgrade helper notices and complains
        self.assertTrue(
            'advertising' in
            localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))
        
    def test_go_to_basic_from_plus_no_advertising_msg(self):
        # Start out in Plus
        self.site_location.tier_name = 'plus'
        self.site_location.save()

        # Delete user #2 so that we have only 1 admin, the super-user
        self.assertEqual(2, localtv.tiers.number_of_admins_including_superuser())
        User.objects.get(username='admin').delete()

        # Go to basic, noting that we will no 'advertising' message
        self.assertTrue(
            'advertising' not in
            localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))
        
    def test_go_to_basic_from_max_lose_custom_domain(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Make our site.domain be myawesomesite.example.com
        self.site_location.site.domain = 'myawesomesite.example.com'
        self.site_location.site.save()

        # Get warnings for downgrade.
        self.assertTrue(
            'customdomain' in
            localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))

    def test_go_to_basic_from_max_with_a_noncustom_domain(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Make our site.domain be within mirocommunity.org
        self.site_location.site.domain = 'myawesomesite.mirocommunity.org'
        self.site_location.site.save()

        # Get warnings for downgrade.
        self.assertFalse(
            'customdomain' in
            localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))

    def test_go_to_basic_with_one_admin(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Delete user #2 so that we have only 1 admin, the super-user
        self.assertEqual(2, localtv.tiers.number_of_admins_including_superuser())
        User.objects.get(username='admin').delete()

        # Now we have 1 admin, namely the super-user
        self.assertEqual(1, localtv.tiers.number_of_admins_including_superuser())

        # Verify that the basic account type only permits 1
        self.assertEqual(1, localtv.tiers.Tier('basic').admins_limit())

        # Now check what messages we would generate if we dropped down
        # to basic.
        self.assertTrue(
            'admins' not in localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))

        # Try pushing the number of admins down to 1, which should change nothing.
        self.assertFalse(localtv.tiers.push_number_of_admins_down(1))
        # Still one admin.
        self.assertEqual(1, localtv.tiers.number_of_admins_including_superuser())

    def test_go_to_basic_with_two_admins(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Verify that we started with 2 admins, including the super-user
        self.assertEqual(2, localtv.tiers.number_of_admins_including_superuser())

        # Verify that the basic account type only permits 1
        self.assertEqual(1, localtv.tiers.Tier('basic').admins_limit())

        # Now check what messages we would generate if we dropped down
        # to basic.
        self.assertTrue('admins' in
                        localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))

        # Well, good -- that means we have to deal with them.
        # Run a function that 
        # Try pushing the number of admins down to 1, which should change nothing.
        usernames = localtv.tiers.push_number_of_admins_down(1)
        self.assertEqual(set(['admin']), usernames)
        # Still two admins -- the above does a dry-run by default.
        self.assertEqual(2, localtv.tiers.number_of_admins_including_superuser())

        # Re-do it for real.
        usernames = localtv.tiers.push_number_of_admins_down(1, actually_demote_people=True)
        self.assertEqual(set(['admin']), usernames)
        self.assertEqual(1, localtv.tiers.number_of_admins_including_superuser())
        
    def test_non_active_users_do_not_count_as_admins(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Verify that we started with 2 admins, including the super-user
        self.assertEqual(2, localtv.tiers.number_of_admins_including_superuser())

        # If we make the 'admin' person not is_active, now there is only "1" admin
        u = User.objects.get(username='admin')
        u.is_active = False
        u.save()
        self.assertEqual(1, localtv.tiers.number_of_admins_including_superuser())
        
    def test_go_to_basic_with_a_custom_theme(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Create two themes -- one bundled, and one not.
        Theme.objects.create(name='a bundled guy', bundled=True, site_id=self.site_location.site_id)
        Theme.objects.create(name='a custom guy', default=True, site_id=self.site_location.site_id)
        
        # Now, make sure that the downgrade helper notices and complains
        self.assertTrue('customtheme' in 
                        localtv.tiers.user_warnings_for_downgrade(new_tier_name='premium'))
        
        # For now, the default theme is still the bundled one.
        self.assertFalse(Theme.objects.get_default().bundled)

        # "Transition" from max to max, to make sure the theme stays
        self.site_location.save()
        self.assertFalse(Theme.objects.get_default().bundled)

        # Now, force the transition
        self.site_location.tier_name = 'premium'
        self.site_location.save()
        # Check that the user is now on a bundled theme
        self.assertTrue(Theme.objects.get_default().bundled)

    @mock.patch('localtv.tiers.Tier.videos_limit', videos_limit_of_two)
    def test_go_to_basic_with_too_many_videos(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Create three published videos
        for k in range(3):
            Video.objects.create(site_id=self.site_location.site_id, status=Video.ACTIVE)
        self.assertTrue('videos' in
                        localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))

        # We can find 'em all, right?
        self.assertEqual(3, Video.objects.active().count())

        # Do the downgrade -- there should only be two active videos now
        self.site_location.tier_name = 'basic'
        self.site_location.save()
        self.assertEqual(2, Video.objects.active().count())

        # Make sure it's video 0 that is disabled
        self.assertEqual(Video.UNAPPROVED,
                         Video.objects.all().order_by('pk')[0].status)

    @mock.patch('localtv.models.SiteLocation.enforce_tiers', mock.Mock(return_value=False))
    @mock.patch('localtv.tiers.Tier.videos_limit', videos_limit_of_two)
    def test_go_to_basic_with_too_many_videos_but_do_not_enforce(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Create three published videos
        for k in range(3):
            Video.objects.create(site_id=self.site_location.site_id, status=Video.ACTIVE)
        self.assertTrue('videos' in
                        localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))

        # We can find 'em all, right?
        self.assertEqual(3,Video.objects.active().count())

        # Do the downgrade -- there should still be three videos because enforcement is disabled
        self.site_location.tier_name = 'basic'
        self.site_location.save()
        self.assertEqual(3,Video.objects.active().count())

    def test_go_to_basic_with_a_custom_theme_that_is_not_enabled(self):
        '''Even if the custom themes are not the default ones, if they exist, we should
        let the user know that it won't be accessible anymore.'''

        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Create two themes -- one bundled, and one not.
        Theme.objects.create(name='a bundled guy', bundled=True, default=True, site_id=self.site_location.site_id)
        Theme.objects.create(name='a custom guy', default=False, site_id=self.site_location.site_id)
        
        # Now, make sure that the downgrade helper notices and complains
        self.assertTrue('customtheme' in
                        localtv.tiers.user_warnings_for_downgrade(new_tier_name='premium'))
        
    def test_go_to_basic_with_a_custom_theme_that_is_not_enabled_from_a_plan_without_custom_themes(self):
        '''If the custom themes are not the default ones, and if the
        current tier does not permit custom themes, then do not bother
        telling the user that they may not use them.'''
        # Start out in Plus, where default themes are disabled.
        self.site_location.tier_name = 'plus'
        self.site_location.save()

        # Create two themes -- one bundled, and one not. Default is bundled.
        Theme.objects.create(name='a bundled guy', default=True, bundled=True, site_id=self.site_location.site_id)
        Theme.objects.create(name='a custom guy', default=False, site_id=self.site_location.site_id)
        
        # Now, make sure that the downgrade helper notices and complains
        self.assertTrue('customtheme' not in
                        localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))
        
    def test_go_to_max_with_a_custom_theme_that_is_not_enabled_from_a_plan_without_custom_themes(self):
        '''If the custom themes are not the default ones, and if the
        current tier does not permit custom themes, then do not bother
        telling the user that they may not use them.'''
        # Start out in Plus, where default themes are disabled.
        self.site_location.tier_name = 'plus'
        self.site_location.save()

        # Create two themes -- one bundled, and one not. Default is bundled.
        Theme.objects.create(name='a bundled guy', default=True, bundled=True, site_id=self.site_location.site_id)
        Theme.objects.create(name='a custom guy', default=False, site_id=self.site_location.site_id)
        
        # Now, make sure that the downgrade helper notices and complains
        self.assertTrue('customtheme' not in
                        localtv.tiers.user_warnings_for_downgrade(new_tier_name='max'))



class AdminDashboardLoadsWithoutError(BaseTestCase):
    url = reverse('localtv_admin_index')

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

class NoEnforceMode(BaseTestCase):
    def test_theme_uploading_with_enforcement(self):
        permit = localtv.tiers.Tier('basic').enforce_permit_custom_template()
        self.assertFalse(permit)

    @mock.patch('localtv.models.SiteLocation.enforce_tiers', mock.Mock(return_value=False))
    def test_theme_uploading_without_enforcement(self):
        permit = localtv.tiers.Tier('basic').enforce_permit_custom_template()
        self.assertTrue(permit)

class DowngradingSevenAdmins(BaseTestCase):
    fixtures = BaseTestCase.fixtures + ['five_more_admins']

    def test_go_to_plus_with_seven_admins(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Verify that we started with 2 admins, including the super-user
        self.assertEqual(7, localtv.tiers.number_of_admins_including_superuser())

        # Verify that the plus account type only permits 5
        self.assertEqual(5, localtv.tiers.Tier('plus').admins_limit())

        # Now check what messages we would generate if we dropped down
        # to basic.
        self.assertTrue('admins' in
                        localtv.tiers.user_warnings_for_downgrade(new_tier_name='basic'))

        # Well, good -- that means we have to deal with them.
        # Run a function that 
        # Try pushing the number of admins down to 1, which should change nothing.
        usernames = localtv.tiers.push_number_of_admins_down(5)
        self.assertEqual(set(['admin8', 'admin9']), usernames)
        # Still two admins -- the above does a dry-run by default.
        self.assertEqual(7, localtv.tiers.number_of_admins_including_superuser())

        # Re-do it for real.
        usernames = localtv.tiers.push_number_of_admins_down(5, actually_demote_people=True)
        self.assertEqual(set(['admin8', 'admin9']), usernames)
        self.assertEqual(5, localtv.tiers.number_of_admins_including_superuser())

class NightlyTiersEmails(BaseTestCase):
    fixtures = BaseTestCase.fixtures

    def setUp(self):
        super(NightlyTiersEmails, self).setUp()
        self.assertEqual(len(mail.outbox), 0)
        self.admin = localtv.tiers.get_main_site_admin()
        self.admin.last_login = datetime.datetime.utcnow()
        self.admin.save()

        from localtv.management.commands import nightly_tiers_events
        self.tiers_cmd = nightly_tiers_events.Command()

    def test_inactive_site_warning(self):
        return # FIXME: Disabling for now.
        # Set up the admin so that the last login was 90 days ago (which should be
        # long enough ago that the site is "inactive")
        self.admin.last_login = datetime.datetime.utcnow() - datetime.timedelta(days=90)
        self.admin.save()
        self.assertFalse(self.site_location.inactive_site_warning_sent)

        # Make sure it sends an email...
        self.tiers_cmd.handle()
        self.assertEqual(len(mail.outbox), 1)
        mail.outbox = []

        # And make sure the SiteLocation knows that the email was sent...
        self.assertTrue(self.site_location.inactive_site_warning_sent)

        # ..so that the next time, it doesn't send any email.
        self.tiers_cmd.handle()
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('localtv.tiers.Tier.remaining_videos_as_proportion', mock.Mock(return_value=0.2))
    def test_video_allotment(self):
        # First, it sends an email. But it saves a note in the SiteLocation...
        self.tiers_cmd.handle()
        self.assertEqual(len(mail.outbox), 1)
        mail.outbox = []

        # ..so that the next time, it doesn't send any email.
        self.tiers_cmd.handle()
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('localtv.models.TierInfo.time_until_free_trial_expires', mock.Mock(return_value=datetime.timedelta(days=7)))
    def test_free_trial_nearly_up_notification_false(self):
        self.tiers_cmd.handle()
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('localtv.models.TierInfo.time_until_free_trial_expires', mock.Mock(return_value=datetime.timedelta(days=5)))
    def test_free_trial_nearly_up_notification_true(self):
        self.tiers_cmd.handle()
        self.assertEqual(len(mail.outbox), 1)
        mail.outbox = []

        # Make sure it does not want to send it again
        self.tiers_cmd.handle()
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('localtv.models.TierInfo.time_until_free_trial_expires', mock.Mock(return_value=datetime.timedelta(days=-1)))
    def test_free_trial_negative(self):
        self.assertRaises(ValueError, self.tiers_cmd.handle, ())
        self.assertEqual(len(mail.outbox), 0)
        mail.outbox = []

class SendWelcomeEmailTest(BaseTestCase):

    def test(self):
        from localtv.management.commands import send_welcome_email
        cmd = send_welcome_email.Command()
        cmd.handle()
        self.assertEqual(len(mail.outbox), 1)

    def test_do_not_send_twice(self):
        self.test()
        mail.outbox = []
        from localtv.management.commands import send_welcome_email
        cmd = send_welcome_email.Command()
        cmd.handle()
        self.assertEqual(len(mail.outbox), 0) # zero this time.

class SendWelcomeEmailTestForSiteStartedAsBasic(BaseTestCase):
    target_tier_name = 'basic'

    @mock.patch('localtv.management.commands.send_welcome_email.Command.actually_send')
    def test_delayed_welcome_email_with_flag_with_successful_upgrade(self, mock_send):
        # When we create a site in a paid tier, we set the
        # should_send_welcome_email_on_paypal_event flag to True.
        #
        # This signifies that we are waiting for the user to go to
        # PayPal before we send the welcome email. So there are two
        # cases:
        #
        # This test method tests the case where the user successfully gets
        # through the process and calls the _paypal_return admin view.
        #
        # (Note that, in theory, the user could rig things carefully so
        # that _paypal_return() gets called, since we don't validate the
        # IPN stuff through _paypal_return(). But the IPN/subscription
        # validation stuff is handled in a separate part of code.)

        # We mock out send_welcome_email's .handle() so that we know if it
        # gets called.

        # No call yet.
        self.assertFalse(mock_send.called)
        self.assertFalse(TierInfo.objects.get_current(
                ).already_sent_welcome_email)

        # Prerequisite:
        ti = TierInfo.objects.get_current()
        ti.should_send_welcome_email_on_paypal_event = True
        ti.save()

        # No call yet.
        self.assertFalse(mock_send.called)
        self.assertTrue(TierInfo.objects.get_current(
                ).should_send_welcome_email_on_paypal_event)

        # Whatever changes the user makes to the SiteLocation should not
        # cause sending, so long as they don't adjust the tier_name.
        site_location = SiteLocation.objects.get_current()
        site_location.tagline = 'my site rules'
        site_location.save()
        # No call yet. Tier Info still retains the flag.
        self.assertFalse(mock_send.called)
        self.assertTrue(TierInfo.objects.get_current(
                ).should_send_welcome_email_on_paypal_event)
        site_location = SiteLocation.objects.get_current()
        self.assertEqual('basic', site_location.tier_name)

        # Now, call _paypal_return() as if the user got there from PayPal.
        localtv.admin.tiers._paypal_return('plus')

        # Make sure the email got sent
        self.assertTrue(mock_send.called)
        # Make sure the tier_name is plus, really, and that the flag is
        # now set to False.
        site_location = SiteLocation.objects.get_current()
        self.assertEqual('plus', site_location.tier_name)
        self.assertFalse(TierInfo.objects.get_current(
                ).should_send_welcome_email_on_paypal_event)

    @mock.patch('localtv.management.commands.send_welcome_email.Command.actually_send')
    def test_delayed_welcome_email_with_flag_with_unsuccessful_upgrade(self,
                                                                       mock_send):
        # Okay, so let's say that you thought you were going to sign
        # up for a 'plus' account.
        #
        # But then you go to PayPal and realize you forgot your password.
        # "Whatever," you figure, and you log in and use the new MC site.
        #
        # What should happen is:
        # - Your site got created as 'basic' at the start.
        # - We don't send you the welcome email because we hoped you would
        #   finish the sign-up process in a non-basic tier.
        # - Then the twice-an-hour cron job runs.
        # - First, it runs when the time delta is less than 30 minutes, in which
        #   case we're still hoping that you will finish up with PayPal.
        # - Then it runs again, and it's more than 30 minutes. So we send you
        #   a welcome email for the tier you are in (basic), and we remove the
        #   flag that says we are expecting you to finish the PayPal process.

        # Setup
        # Pre-requisite:
        NOW = datetime.datetime.utcnow()
        PLUS_THIRTY_MIN = NOW + datetime.timedelta(minutes=30)
        ti = TierInfo.objects.get_current()
        ti.should_send_welcome_email_on_paypal_event = True
        ti.waiting_on_payment_until = PLUS_THIRTY_MIN
        ti.save()

        self.assertFalse(mock_send.called)
        self.assertEqual(SiteLocation.objects.get_current().tier_name,
                         'basic')

        # Whatever changes the user makes to the SiteLocation should not
        # cause sending, so long as they don't adjust the tier_name.
        site_location = SiteLocation.objects.get_current()
        site_location.tagline = 'my site rules'
        site_location.save()
        # No call yet. Tier Info still retains the flag.
        self.assertFalse(mock_send.called)
        self.assertTrue(TierInfo.objects.get_current(
                ).should_send_welcome_email_on_paypal_event)
        site_location = SiteLocation.objects.get_current()
        self.assertEqual('basic', site_location.tier_name)

        PLUS_TEN_MIN = NOW + datetime.timedelta(minutes=10)
        PLUS_FORTY_MIN = NOW + datetime.timedelta(minutes=40)

        cmd = localtv.management.commands.check_frequently_for_invalid_tiers_state.Command()
        cmd.stop_waiting_if_we_have_to(PLUS_TEN_MIN)

        # Should be no change + no email
        self.assertFalse(mock_send.called)

        # re-call even later
        cmd.stop_waiting_if_we_have_to(PLUS_FORTY_MIN)
        self.assertTrue(mock_send.called)
        self.assertFalse(TierInfo.objects.get_current(
                ).should_send_welcome_email_on_paypal_event)
        self.assertFalse(TierInfo.objects.get_current(
                ).waiting_on_payment_until)

class TestDisableEnforcement(BaseTestCase):

    def testTrue(self):
        self.assertTrue(SiteLocation.enforce_tiers(override_setting=False))

    def testFalse(self):
        self.assertFalse(SiteLocation.enforce_tiers(override_setting=True))

class TestTiersComplianceEmail(BaseTestCase):
    def setUp(self):
        super(TestTiersComplianceEmail, self).setUp()
        self.site_location.tier_name = 'basic'
        self.site_location.save()
        from localtv.management.commands import send_tiers_compliance_email
        self.cmd = send_tiers_compliance_email.Command()

    def test_email_when_over_video_limit(self):
        for n in range(1000):
            Video.objects.create(site_id=1, status=Video.ACTIVE)
        # The first time round, we should get an email.
        self.cmd.handle()
        self.assertEqual(1,
                         len(mail.outbox))
        # Clear the outbox. When we run the command again, we should not
        # get an email.
        mail.outbox = []
        self.cmd.handle()
        self.assertEqual(0,
                         len(mail.outbox))

    def test_email_when_within_limits(self):
        self.cmd.handle()
        self.assertEqual(1,
                         len(mail.outbox))

    def test_no_email_when_over_video_limits_but_database_says_it_has_been_sent(self):
        ti = TierInfo.objects.get_current()
        ti.already_sent_tiers_compliance_email = True
        ti.save()

        for n in range(1000):
            Video.objects.create(site_id=1, status=Video.ACTIVE)
        self.cmd.handle()
        self.assertEqual(0,
                         len(mail.outbox))

class DowngradingCanNotifySupportAboutCustomDomain(BaseTestCase):
    fixtures = BaseTestCase.fixtures

    def setUp(self):
        super(DowngradingCanNotifySupportAboutCustomDomain, self).setUp()
        self.old_zendesk_value = getattr(settings, 'LOCALTV_USE_ZENDESK', None)
        settings.LOCALTV_USE_ZENDESK = True

    @mock.patch('localtv.models.SiteLocation.enforce_tiers', mock.Mock(return_value=True))
    def test(self):
        # Start out in Executive mode, by default
        self.assertEqual(self.site_location.tier_name, 'max')

        # Give the site a custom domain
        site = self.site_location.site
        site.domain = 'custom.example.com'
        site.save()

        # Make sure it stuck
        self.assertEqual(self.site_location.site.domain,
                         'custom.example.com')

        # There are no emails in the outbox yet
        self.assertEqual(0,
                         len(mail.outbox))

        # Bump down to 'basic'.
        self.site_location.tier_name = 'basic'
        self.site_location.save()

        self.assertEqual([], mail.outbox)
        import localtv.zendesk
        self.assertEqual(1, len(localtv.zendesk.outbox))

    def tearDown(self):
        super(DowngradingCanNotifySupportAboutCustomDomain, self).tearDown()
        settings.LOCALTV_USE_ZENDESK = self.old_zendesk_value

class IpnIntegration(BaseTestCase):
    def setUp(self):
        # Call superclass setUp()
        super(IpnIntegration, self).setUp()

        # Set current tier to 'basic'
        self.site_location.tier_name = 'basic'
        self.site_location.save()

        # At the start of this test, we have no current recurring payment profile
        new_tier_info = TierInfo.objects.get_current()
        self.assertFalse(new_tier_info.current_paypal_profile_id)

        # Make sure there is a free trial available
        self.tier_info.free_trial_available = True
        self.tier_info.free_trial_started_on = None
        self.tier_info.save()

        self.c = Client()
        self.c.login(username='superuser', password='superuser')

        self.old_zendesk_value = getattr(settings, 'LOCALTV_USE_ZENDESK', None)
        settings.LOCALTV_USE_ZENDESK = True

    def tearDown(self):
        super(IpnIntegration, self).tearDown()
        settings.LOCALTV_USE_ZENDESK = self.old_zendesk_value

    def upgrade_and_submit_ipn(self):
        self.assertTrue(TierInfo.objects.get_current().free_trial_available)

        # POST to the begin_free_trial element...
        url = reverse('localtv_admin_begin_free_trial',
                      kwargs={'payment_secret': self.tier_info.get_payment_secret()})
        response = self.c.get(url,
                               {'target_tier_name': 'plus'})

        # Make sure we switched
        self.assertEqual('plus', self.site_location.tier_name)

        # Discover that we still have no paypal profile, because PayPal took a few sec to submit the IPN...
        new_tier_info = TierInfo.objects.get_current()
        self.assertFalse(new_tier_info.current_paypal_profile_id)

        # Check that we are in a free trial (should be!)
        self.assertTrue(new_tier_info.in_free_trial)
        self.assertFalse(new_tier_info.free_trial_available)
        message = mail.outbox[0].body
        self.assertFalse('until midnight on None' in message)

        # Now, PayPal sends us the IPN.
        ipn_data = {u'last_name': u'User', u'receiver_email': settings.PAYPAL_RECEIVER_EMAIL, u'residence_country': u'US', u'mc_amount1': u'0.00', u'invoice': u'premium', u'payer_status': u'verified', u'txn_type': u'subscr_signup', u'first_name': u'Test', u'item_name': u'Miro Community subscription (plus)', u'charset': u'windows-1252', u'custom': u'plus for example.com', u'notify_version': u'3.0', u'recurring': u'1', u'test_ipn': u'1', u'business': settings.PAYPAL_RECEIVER_EMAIL, u'payer_id': u'SQRR5KCD7Z266', u'period3': u'1 M', u'period1': u'30 D', u'verify_sign': u'AKcOzwh6cb1eCtGrfvM.18Ri5hWDAWoRIoMoZm39KHDsLIoVZyWJDM7B', u'subscr_id': u'I-MEBGA2YXPNJK', u'amount3': unicode(PLUS_COST), u'amount1': u'0.00', u'mc_amount3': unicode(PLUS_COST), u'mc_currency': u'USD', u'subscr_date': u'12:06:48 Feb 17, 2011 PST', u'payer_email': u'paypal_1297894110_per@s.asheesh.org', u'reattempt': u'1'}
        url = reverse('localtv_admin_ipn_endpoint',
                      kwargs={'payment_secret': self.tier_info.get_payment_secret()})

        Client().post(url,
                      ipn_data)

        # Make sure SiteLocation recognizes we are in 'plus'
        self.assertEqual(self.site_location.tier_name, 'plus')

        new_tier_info = TierInfo.objects.get_current()
        self.assertTrue(new_tier_info.in_free_trial)
        self.assertFalse(new_tier_info.free_trial_available)

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='VERIFIED'))
    def test_upgrade_and_submit_ipn_skipping_free_trial_post(self):
        # If the user upgrades but neglects to POST to the begin_free_trial handler
        new_tier_info = TierInfo.objects.get_current()
        self.assertFalse(new_tier_info.current_paypal_profile_id)
        self.assertFalse(new_tier_info.in_free_trial)
        self.assertTrue(new_tier_info.free_trial_available)

        self.upgrade_and_submit_ipn_skipping_free_trial_post()

        # Make sure SiteLocation recognizes we are in 'plus'
        self.assertEqual(self.site_location.tier_name, 'plus')

        # Make sure we are in a free trial, etc.
        new_tier_info = TierInfo.objects.get_current()
        self.assertTrue(new_tier_info.in_free_trial)
        self.assertFalse(new_tier_info.free_trial_available)

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='VERIFIED'))
    def upgrade_and_submit_ipn_skipping_free_trial_post(self, override_amount3=None):
        if override_amount3:
            amount3 = override_amount3
        else:
            amount3 = unicode(PLUS_COST)

        # Now, PayPal sends us the IPN.
        ipn_data = {u'last_name': u'User', u'receiver_email': settings.PAYPAL_RECEIVER_EMAIL, u'residence_country': u'US', u'mc_amount1': u'0.00', u'invoice': u'premium', u'payer_status': u'verified', u'txn_type': u'subscr_signup', u'first_name': u'Test', u'item_name': u'Miro Community subscription (plus)', u'charset': u'windows-1252', u'custom': u'plus for example.com', u'notify_version': u'3.0', u'recurring': u'1', u'test_ipn': u'1', u'business': settings.PAYPAL_RECEIVER_EMAIL, u'payer_id': u'SQRR5KCD7Z266', u'period3': u'1 M', u'period1': u'30 D', u'verify_sign': u'AKcOzwh6cb1eCtGrfvM.18Ri5hWDAWoRIoMoZm39KHDsLIoVZyWJDM7B', u'subscr_id': u'I-MEBGA2YXPNJK', u'amount3': amount3, u'amount1': u'0.00', u'mc_amount3': amount3, u'mc_currency': u'USD', u'subscr_date': u'12:06:48 Feb 17, 2011 PST', u'payer_email': u'paypal_1297894110_per@s.asheesh.org', u'reattempt': u'1'}
        url = reverse('localtv_admin_ipn_endpoint',
                      kwargs={'payment_secret': self.tier_info.get_payment_secret()})

        response = Client().post(url,
                      ipn_data)
        self.assertEqual('OKAY', response.content.strip())

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='VERIFIED'))
    def upgrade_including_prorated_duration_and_amount(self, amount1, amount3, period1):
        ipn_data = {u'last_name': u'User', u'receiver_email': settings.PAYPAL_RECEIVER_EMAIL, u'residence_country': u'US', u'mc_amount1': amount1, u'invoice': u'premium', u'payer_status': u'verified', u'txn_type': u'subscr_signup', u'first_name': u'Test', u'item_name': u'Miro Community subscription (plus)', u'charset': u'windows-1252', u'custom': u'prorated change', u'notify_version': u'3.0', u'recurring': u'1', u'test_ipn': u'1', u'business': settings.PAYPAL_RECEIVER_EMAIL, u'payer_id': u'SQRR5KCD7Z266', u'period3': u'1 M', u'period1': period1, u'verify_sign': u'AKcOzwh6cb1eCtGrfvM.18Ri5hWDAWoRIoMoZm39KHDsLIoVZyWJDM7B', u'subscr_id': u'I-MEBGA2YXPNJK', u'amount3': amount3, u'amount1': amount1, u'mc_amount3': amount3, u'mc_currency': u'USD', u'subscr_date': u'12:06:48 Feb 20, 2011 PST', u'payer_email': u'paypal_1297894110_per@s.asheesh.org', u'reattempt': u'1'}
        url = reverse('localtv_admin_ipn_endpoint',
                      kwargs={'payment_secret': self.tier_info.get_payment_secret()})

        response = Client().post(url,
                      ipn_data)
        self.assertEqual('OKAY', response.content.strip())

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='VERIFIED'))
    def submit_ipn_subscription_modify(self, override_amount3=None, override_subscr_id=None):
        if override_amount3:
            amount3 = override_amount3
        else:
            amount3 = unicode(PLUS_COST)

        if override_subscr_id:
            subscr_id = override_subscr_id
        else:
            subscr_id = u'I-MEBGA2YXPNJK'

        # Now, PayPal sends us the IPN.
        ipn_data = {u'last_name': u'User', u'receiver_email': settings.PAYPAL_RECEIVER_EMAIL, u'residence_country': u'US', u'mc_amount1': u'0.00', u'invoice': u'premium', u'payer_status': u'verified', u'txn_type': u'subscr_modify', u'first_name': u'Test', u'item_name': u'Miro Community subscription (plus)', u'charset': u'windows-1252', u'custom': u'plus for example.com', u'notify_version': u'3.0', u'recurring': u'1', u'test_ipn': u'1', u'business': settings.PAYPAL_RECEIVER_EMAIL, u'payer_id': u'SQRR5KCD7Z266', u'period3': u'1 M', u'period1': u'30 D', u'verify_sign': u'AKcOzwh6cb1eCtGrfvM.18Ri5hWDAWoRIoMoZm39KHDsLIoVZyWJDM7B', u'subscr_id': subscr_id, u'amount3': amount3, u'amount1': u'0.00', u'mc_amount3': amount3, u'mc_currency': u'USD', u'subscr_date': u'12:06:48 Feb 17, 2011 PST', u'payer_email': u'paypal_1297894110_per@s.asheesh.org', u'reattempt': u'1'}
        url = reverse('localtv_admin_ipn_endpoint',
                      kwargs={'payment_secret': self.tier_info.get_payment_secret()})

        response = Client().post(url,
                      ipn_data)
        self.assertEqual('OKAY', response.content.strip())

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='VERIFIED'))
    def submit_ipn_subscription_cancel(self, override_subscr_id=None):
        if override_subscr_id:
            subscr_id = override_subscr_id
        else:
            subscr_id = u'I-MEBGA2YXPNJK'

        # Now, PayPal sends us the IPN.
        ipn_data = {u'last_name': u'User', u'receiver_email': settings.PAYPAL_RECEIVER_EMAIL, u'residence_country': u'US', u'mc_amount1': u'0.00', u'invoice': u'premium', u'payer_status': u'verified', u'txn_type': u'subscr_cancel', u'first_name': u'Test', u'item_name': u'Miro Community subscription (plus)', u'charset': u'windows-1252', u'custom': u'plus for example.com', u'notify_version': u'3.0', u'recurring': u'1', u'test_ipn': u'1', u'business': settings.PAYPAL_RECEIVER_EMAIL, u'payer_id': u'SQRR5KCD7Z266', u'period3': u'1 M', u'period1': u'30 D', u'verify_sign': u'AKcOzwh6cb1eCtGrfvM.18Ri5hWDAWoRIoMoZm39KHDsLIoVZyWJDM7B', u'subscr_id': subscr_id, u'amount1': u'0.00', u'mc_currency': u'USD', u'subscr_date': u'12:06:48 Feb 17, 2011 PST', u'payer_email': u'paypal_1297894110_per@s.asheesh.org', u'reattempt': u'1'}
        url = reverse('localtv_admin_ipn_endpoint',
                      kwargs={'payment_secret': self.tier_info.get_payment_secret()})

        response = Client().post(url,
                      ipn_data)
        self.assertEqual('OKAY', response.content.strip())

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='VERIFIED'))
    def test_upgrade_between_paid_tiers(self):
        self.test_success()
        self.assertEqual(self.site_location.tier_name, 'plus')

        self.upgrade_between_paid_tiers()

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='VERIFIED'))
    def upgrade_between_paid_tiers(self):
        # Now, we get an IPN for $35, which should move us to 'premium'
        # Now, PayPal sends us the IPN.
        mail.outbox = []
        ipn_data = {u'last_name': u'User', u'receiver_email': settings.PAYPAL_RECEIVER_EMAIL, u'residence_country': u'US', u'mc_amount1': u'0.00', u'invoice': u'premium', u'payer_status': u'verified', u'txn_type': u'subscr_signup', u'first_name': u'Test', u'item_name': u'Miro Community subscription (plus)', u'charset': u'windows-1252', u'custom': u'plus for example.com', u'notify_version': u'3.0', u'recurring': u'1', u'test_ipn': u'1', u'business': settings.PAYPAL_RECEIVER_EMAIL, u'payer_id': u'SQRR5KCD7Z266', u'period3': u'1 M', u'period1': u'', u'verify_sign': u'AKcOzwh6cb1eCtGrfvM.18Ri5hWDAWoRIoMoZm39KHDsLIoVZyWJDM7B', u'subscr_id': u'I-MEBGA2YXPNJR', u'amount3': unicode(PREMIUM_COST), u'amount1': u'0.00', u'mc_amount3': unicode(PREMIUM_COST), u'mc_currency': u'USD', u'subscr_date': u'12:06:48 Feb 17, 2011 PST', u'payer_email': u'paypal_1297894110_per@s.asheesh.org', u'reattempt': u'1'}
        url = reverse('localtv_admin_ipn_endpoint',
                      kwargs={'payment_secret': self.tier_info.get_payment_secret()})

        Client().post(url,
                      ipn_data)

        # Make sure SiteLocation recognizes we are in 'premium'
        fresh_site_location = SiteLocation.objects.get_current()
        self.assertEqual(fresh_site_location.tier_name, 'premium')

        ti = TierInfo.objects.get_current()
        self.assertEqual(ti.current_paypal_profile_id, 'I-MEBGA2YXPNJR') # the new one
        self.assertTrue(ti.payment_due_date > datetime.datetime(2011, 3, 19, 0, 0, 0))
        import localtv.zendesk
        self.assertEqual(len([msg for msg in localtv.zendesk.outbox
                              if 'cancel a recurring payment profile' in msg['subject']]), 1)
        localtv.zendesk.outbox = [] 
        mail.outbox = []

        # PayPal eventually sends us the IPN cancelling the old subscription, because someone
        # in the MC team ends it.
        ipn_data = {u'last_name': u'User', u'receiver_email': settings.PAYPAL_RECEIVER_EMAIL, u'residence_country': u'US', u'mc_amount1': u'0.00', u'invoice': u'premium', u'payer_status': u'verified', u'txn_type': u'subscr_cancel', u'first_name': u'Test', u'item_name': u'Miro Community subscription (plus)', u'charset': u'windows-1252', u'custom': u'plus for example.com', u'notify_version': u'3.0', u'recurring': u'1', u'test_ipn': u'1', u'business': settings.PAYPAL_RECEIVER_EMAIL, u'payer_id': u'SQRR5KCD7Z266', u'period3': u'1 M', u'period1': u'30 D', u'verify_sign': u'AKcOzwh6cb1eCtGrfvM.18Ri5hWDAWoRIoMoZm39KHDsLIoVZyWJDM7B', u'subscr_id': u'I-MEBGA2YXPNJK', u'amount3': unicode(PLUS_COST), u'amount1': u'0.00', u'mc_amount3': unicode(PLUS_COST), u'mc_currency': u'USD', u'subscr_date': u'12:06:48 Feb 17, 2011 PST', u'payer_email': u'paypal_1297894110_per@s.asheesh.org', u'reattempt': u'1'}
        url = reverse('localtv_admin_ipn_endpoint',
                      kwargs={'payment_secret': self.tier_info.get_payment_secret()})

        Client().post(url,
                      ipn_data)

        # Make sure SiteLocation still recognizes we are in 'premium'
        fresh_site_location = SiteLocation.objects.get_current()
        self.assertEqual(fresh_site_location.tier_name, 'premium')

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='VERIFIED'))
    def test_success(self):
        self.upgrade_and_submit_ipn()
        tier_info = TierInfo.objects.get_current()
        self.assertEqual(tier_info.current_paypal_profile_id, 'I-MEBGA2YXPNJK')

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='VERIFIED'))
    def test_payment_success(self):
        self.upgrade_and_submit_ipn()
        tier_info = TierInfo.objects.get_current()
        self.assertEqual(tier_info.current_paypal_profile_id, 'I-MEBGA2YXPNJK')

        # Send ourselves a payment IPN.
        ipn_data = {u'last_name': u'User', u'receiver_email': settings.PAYPAL_RECEIVER_EMAIL, u'residence_country': u'US', u'mc_amount1': u'0.00', u'invoice': u'premium', u'payer_status': u'verified', u'txn_type': u'subscr_payment', u'txn_id':u'S-4LF64589B35985347', u'payment_status': 'Completed', u'first_name': u'Test', u'item_name': u'Miro Community subscription (plus)', u'charset': u'windows-1252', u'custom': u'plus for example.com', u'notify_version': u'3.0', u'recurring': u'1', u'test_ipn': u'1', u'business': settings.PAYPAL_RECEIVER_EMAIL, u'payer_id': u'SQRR5KCD7Z266', u'verify_sign': u'AKcOzwh6cb1eCtGrfvM.18Ri5hWDAWoRIoMoZm39KHDsLIoVZyWJDM7B', u'subscr_id': u'I-MEBGA2YXPNJK', u'payment_gross': unicode(PLUS_COST), u'payment_date': u'12:06:48 Mar 17, 2011 PST', u'payer_email': u'paypal_1297894110_per@s.asheesh.org', u'reattempt': u'1'}
        url = reverse('localtv_admin_ipn_endpoint',
                      kwargs={'payment_secret': self.tier_info.get_payment_secret()})

        Client().post(url,
                      ipn_data)
        tier_info_new = TierInfo.objects.get_current()
        self.assertEqual(tier_info_new.current_paypal_profile_id, 'I-MEBGA2YXPNJK')
        # make sure that they've pushed the due date into the future
        self.assertTrue(tier_info_new.payment_due_date > tier_info.payment_due_date)

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='FAILURE'))
    def test_failure(self):
        tier_info = TierInfo.objects.get_current()
        self.assertFalse(tier_info.current_paypal_profile_id) # Should be false at the start

        self.upgrade_and_submit_ipn()
        tier_info = TierInfo.objects.get_current()

        # Because the IPN submitted was invalid, the payment profile ID has not changed.
        self.assertFalse(tier_info.current_paypal_profile_id)

    @mock.patch('paypal.standard.ipn.models.PayPalIPN._postback', mock.Mock(return_value='VERIFIED'))
    def test_downgrade_during_free_trial(self):
        # First, upgrade to 'premium' during the free trial.
        self.upgrade_and_submit_ipn_skipping_free_trial_post(
            unicode(PREMIUM_COST))

        # Make sure it worked
        tierinfo = TierInfo.objects.get_current()
        self.assertEqual('premium', self.site_location.tier_name)
        self.assertTrue(tierinfo.in_free_trial)

        # Now, submit an IPN event for changing the payment amount to '15.00'
        # This should move us down to 'plus'
        self.submit_ipn_subscription_modify(unicode(PLUS_COST))

        # Make sure it worked
        self.assertEqual('plus', SiteLocation.objects.get_current().tier_name)
        tierinfo = TierInfo.objects.get_current()
        self.assertFalse(tierinfo.in_free_trial)

class TestMidMonthPaymentAmounts(BaseTestCase):
    def test_start_of_month(self):
        data = localtv.admin.tiers.generate_payment_amount_for_upgrade(
            start_tier_name='plus', target_tier_name='premium',
            current_payment_due_date=datetime.datetime(2011, 1, 30, 0, 0, 0),
            todays_date=datetime.datetime(2011, 1, 1, 12, 0, 0))
        expected = {'recurring': PREMIUM_COST,
                    'cost_for_prorated_period': int(PREMIUM_COST * 0.44),
                    'days_covered_by_prorating': 28}
        self.assertEqual(data, expected)

    def test_end_of_month(self):
        data = localtv.admin.tiers.generate_payment_amount_for_upgrade(
            start_tier_name='plus', target_tier_name='premium',
            current_payment_due_date=datetime.datetime(2011, 2, 1, 0, 0, 0),
            todays_date=datetime.datetime(2011, 1, 31, 12, 0, 0))
        expected = {'recurring': PREMIUM_COST, 'cost_for_prorated_period': 0, 'days_covered_by_prorating': 0}
        self.assertEqual(data, expected)

class TestUpgradePage(BaseTestCase):
    ### State transition helpers
    def setUp(self):
        self.ipn_integration = None
        super(TestUpgradePage, self).setUp()
        # Always start in 'basic' with a free trial
        import localtv.management.commands.clear_tiers_state
        c = localtv.management.commands.clear_tiers_state.Command()
        import localtv.zendesk
        localtv.zendesk.outbox = []
        c.handle_noargs()

        self.old_zendesk_value = getattr(settings, 'LOCALTV_USE_ZENDESK', None)
        settings.LOCALTV_USE_ZENDESK = True

    def tearDown(self):
        # Note: none of these tests should cause email to be sent.
        self.assertEqual([],
                         [str(k.body) for k in mail.outbox])
        settings.LOCALTV_USE_ZENDESK = self.old_zendesk_value

    ## assertion helpers
    def _assert_upgrade_extra_payments_always_false(self, response):
        extras = response.context['upgrade_extra_payments']
        for thing in extras:
            self.assertFalse(extras[thing])

    def _assert_modify_always_false(self, response):
        self.assertEqual({'basic': False,
                          'plus': False,
                          'premium': False,
                          'max': False},
                         response.context['can_modify_mapping'])

    def _run_method_from_ipn_integration_test_case(self, methodname, *args):
        if self.ipn_integration is None:
            self.ipn_integration = IpnIntegration(methodname)
            self.ipn_integration.setUp()
        getattr(self.ipn_integration, methodname)(*args)

    ## Action helpers
    def _log_in_as_superuser(self):
        c = Client()
        self.assertTrue(c.login(username='superuser', password='superuser'))
        return c

    ## Tests of various cases of the upgrade page
    def test_first_upgrade(self):
        self.assertTrue(self.site_location.tierinfo.free_trial_available)
        c = self._log_in_as_superuser()
        response = c.get(reverse('localtv_admin_tier'))
        self.assertTrue(response.context['offer_free_trial'])
        self._assert_modify_always_false(response)

    def test_upgrade_when_no_free_trial(self):
        ti = TierInfo.objects.get_current()
        ti.free_trial_available = False
        ti.save()
        c = self._log_in_as_superuser()
        response = c.get(reverse('localtv_admin_tier'))
        self.assertFalse(response.context['offer_free_trial'])
        self._assert_modify_always_false(response)

    def test_upgrade_when_within_a_free_trial(self):
        # We start in 'basic' with a free trial.
        # The pre-requisite for this test is that we have transitioned into a tier.
        # So borrow a method from IpnIntegration
        self._run_method_from_ipn_integration_test_case('test_upgrade_and_submit_ipn_skipping_free_trial_post')
        mail.outbox = [] # remove "Congratulations" email

        # Sanity-check the free trial state.
        ti = TierInfo.objects.get_current()
        self.assertFalse(ti.free_trial_available)
        self.assertTrue(ti.in_free_trial)
        self.assertTrue(ti.current_paypal_profile_id)

        # We are in 'plus'. Let's consider what happens when
        # we want to upgrade to 'premium'
        sl = SiteLocation.objects.get_current()
        self.assertEqual('plus', sl.tier_name)

        c = self._log_in_as_superuser()
        response = c.get(reverse('localtv_admin_tier'))
        self.assertFalse(response.context['offer_free_trial'])

        # This should be False because PayPal will not let us substantially
        # increase a recurring payment amount.
        self.assertFalse(response.context['can_modify_mapping']['premium'])

        # There should be no upgrade_extra_payments value, because we are
        # in a free trial.
        self.assertFalse(response.context['upgrade_extra_payments']['premium'])

        # Okay, so go through the PayPal dance.

        # First, pretend the user went to the paypal_return view, and adjusted
        # the tier name, but without actually receiving the IPN.
        localtv.admin.tiers._paypal_return('premium')
        self.assertEqual(SiteLocation.objects.get_current().tier_name, 'premium')
        ti = TierInfo.objects.get_current()
        self.assertEqual('plus', ti.fully_confirmed_tier_name)
        # The tier name is updated, so the backend updates its state.
        # That means we sent a "Congratulations" email:
        message, = [str(k.body) for k in mail.outbox]
        self.assertTrue('Congratulations' in message)
        mail.outbox = []
        ti = TierInfo.objects.get_current()
        self.assertTrue(ti.in_free_trial)

        # Actually do the upgrade
        self._run_method_from_ipn_integration_test_case('upgrade_between_paid_tiers')

        # The above method checks that we successfully send an email to
        # support@ suggesting that the user cancel the old payment.
        #
        # It also simulates a support staff person actually cancelling the
        # old payment.
        sl = SiteLocation.objects.get_current()
        self.assertEqual('premium', sl.tier_name)
        ti = TierInfo.objects.get_current()
        self.assertEqual('', ti.fully_confirmed_tier_name)

        # Now, make sure the backend knows that we are not in a free trial
        self.assertFalse(ti.in_free_trial)

    def test_upgrade_when_within_a_free_trial_with_super_quick_ipn(self):
        # We start in 'basic' with a free trial.
        # The pre-requisite for this test is that we have transitioned into a tier.
        # So borrow a method from IpnIntegration
        self._run_method_from_ipn_integration_test_case('test_upgrade_and_submit_ipn_skipping_free_trial_post')
        mail.outbox = [] # remove "Congratulations" email

        # Sanity-check the free trial state.
        ti = TierInfo.objects.get_current()
        self.assertFalse(ti.free_trial_available)
        self.assertTrue(ti.in_free_trial)
        self.assertTrue(ti.current_paypal_profile_id)

        # We are in 'plus'. Let's consider what happens when
        # we want to upgrade to 'premium'
        sl = SiteLocation.objects.get_current()
        self.assertEqual('plus', sl.tier_name)

        c = self._log_in_as_superuser()
        response = c.get(reverse('localtv_admin_tier'))
        self.assertFalse(response.context['offer_free_trial'])

        # This should be False because PayPal will not let us substantially
        # increase a recurring payment amount.
        self.assertFalse(response.context['can_modify_mapping']['premium'])

        # There should be no upgrade_extra_payments value, because we are
        # in a free trial.
        self.assertFalse(response.context['upgrade_extra_payments']['premium'])

        # Okay, so go through the PayPal dance.

        # Actually do the upgrade
        self._run_method_from_ipn_integration_test_case('upgrade_between_paid_tiers')

        # The above method checks that we successfully send an email to
        # support@ suggesting that the user cancel the old payment.
        #
        # It also simulates a support staff person actually cancelling the
        # old payment.
        sl = SiteLocation.objects.get_current()
        self.assertEqual('premium', sl.tier_name)
        ti = TierInfo.objects.get_current()
        self.assertEqual('', ti.fully_confirmed_tier_name)

        # First, pretend the user went to the paypal_return view, and adjusted
        # the tier name, but without actually receiving the IPN.
        localtv.admin.tiers._paypal_return('premium')
        self.assertEqual(SiteLocation.objects.get_current().tier_name, 'premium')
        ti = TierInfo.objects.get_current()
        self.assertEqual('', ti.fully_confirmed_tier_name)
        # The tier name was already updated, so the backend need not update its state.
        # Therefore, we do a "Congratulations" email:
        self.assertEqual([], mail.outbox)

        # Now, make sure the backend knows that we are not in a free trial
        self.assertFalse(ti.in_free_trial)

    def test_upgrade_from_basic_when_not_within_a_free_trial(self):
        # The pre-requisite for this test is that we have transitioned into a tier.
        # So borrow a method from IpnIntegration
        self._run_method_from_ipn_integration_test_case('test_upgrade_and_submit_ipn_skipping_free_trial_post')
        mail.outbox = [] # remove "Congratulations" email

        # Sanity-check the free trial state.
        ti = TierInfo.objects.get_current()
        self.assertFalse(ti.free_trial_available)
        self.assertTrue(ti.in_free_trial)
        self.assertTrue(ti.current_paypal_profile_id)

        # Cancelling the subscription should put empty out the current paypal ID.
        self._run_method_from_ipn_integration_test_case('submit_ipn_subscription_cancel', ti.current_paypal_profile_id)
        # Sanity-check the free trial state.
        ti = TierInfo.objects.get_current()
        self.assertFalse(ti.free_trial_available)
        self.assertFalse(ti.in_free_trial)
        self.assertFalse(ti.current_paypal_profile_id)
        # We are in 'basic' now.
        sl = SiteLocation.objects.get_current()
        self.assertEqual('basic', sl.tier_name)

        # If we upgrade to a paid tier...
        c = self._log_in_as_superuser()
        response = c.get(reverse('localtv_admin_tier'))
        self.assertFalse(response.context['offer_free_trial'])
        self._assert_modify_always_false(response)
        self._assert_upgrade_extra_payments_always_false(response)

    def test_upgrade_from_paid_when_within_a_free_trial(self):
        # The pre-requisite for this test is that we have transitioned into a tier.
        # So borrow a method from IpnIntegration
        self._run_method_from_ipn_integration_test_case('test_upgrade_and_submit_ipn_skipping_free_trial_post')
        mail.outbox = [] # remove "Congratulations" email

        # Sanity-check the free trial state.
        ti = TierInfo.objects.get_current()
        self.assertFalse(ti.free_trial_available)
        self.assertTrue(ti.in_free_trial)
        self.assertTrue(ti.current_paypal_profile_id)
        first_profile = ti.current_paypal_profile_id
        sl = SiteLocation.objects.get_current()
        self.assertEqual('plus', sl.tier_name)

        # If we want to upgrade... let's look at the upgrade page state:
        c = self._log_in_as_superuser()
        response = c.get(reverse('localtv_admin_tier'))
        self.assertFalse(response.context['offer_free_trial'])
        self._assert_upgrade_extra_payments_always_false(response)
        self._assert_modify_always_false(response) # no modify possible from 'plus'

        # This means that if someone changes the payment amount to $35/mo
        # we will be at 'premium'.
        self._run_method_from_ipn_integration_test_case('upgrade_between_paid_tiers')
        sl = SiteLocation.objects.get_current()
        self.assertEqual('premium', sl.tier_name)
        ti = sl.tierinfo
        self.assertNotEqual(ti.current_paypal_profile_id, first_profile)

    def test_upgrade_from_paid_when_not_within_a_free_trial(self):
        # First, upgrade and downgrade...
        self.test_downgrade_to_paid_not_during_a_trial()

        sl = SiteLocation.objects.get_current()
        self.assertEqual('plus', sl.tier_name)

        # Travel to the future
        with mock.patch('datetime.datetime', Fakedatetime):
            # Now, we have some crazy prorating stuff.
            c = self._log_in_as_superuser()
            response = c.get(reverse('localtv_admin_tier'))

        self.assertFalse(response.context['offer_free_trial'])
        # For the prorating...
        extras = response.context['upgrade_extra_payments']
        premium = extras['premium']
        # The adjusted due date is, like, about 1 day different.
        self.assertTrue(abs((Fakedatetime.utcnow() - (sl.tierinfo.payment_due_date - datetime.timedelta(premium['days_covered_by_prorating']))).days) <= 1)
        # The one-time money bump is more than 2/3 of the difference.
        entire_difference = (localtv.tiers.Tier('premium').dollar_cost() - localtv.tiers.Tier('plus').dollar_cost())
        self.assertTrue(premium['cost_for_prorated_period'] >= (0.667 * entire_difference))
        self._assert_modify_always_false(response) # no modify possible from 'plus'

        # Let's try paying.
        # NOTE: We don't check here what happens if you pay with the wrong
        # pro-rating amount.
        with mock.patch('datetime.datetime', Fakedatetime):
            self._run_method_from_ipn_integration_test_case(
                'upgrade_including_prorated_duration_and_amount', 
                '%d.00' % premium['cost_for_prorated_period'],
                str(PREMIUM_COST),
                '%d D' % premium['days_covered_by_prorating'])
            sl = SiteLocation.objects.get_current()
            self.assertEqual('premium', sl.tier_name)
            # Also, no emails.
            self.assertEqual(set(['superuser@testserver.local']),
                             set([x.to[0] for x in mail.outbox]))
            self.assertEqual(1, len(localtv.zendesk.outbox))
            mail.outbox = []

    def test_downgrade_to_paid_during_a_trial(self):
        # The test gets initialized in 'basic' with a free trial available.
        # First, switch into a free trial of 'max'.
        self._run_method_from_ipn_integration_test_case('upgrade_and_submit_ipn_skipping_free_trial_post', str(MAX_COST))
        mail.outbox = [] # remove "Congratulations" email

        # Sanity-check the free trial state.
        ti = TierInfo.objects.get_current()
        self.assertFalse(ti.free_trial_available)
        self.assertTrue(ti.in_free_trial)
        self.assertTrue(ti.current_paypal_profile_id)
        old_profile = ti.current_paypal_profile_id

        # We are in 'max'. Let's consider what happens when
        # we want to downgrade to 'premium'
        sl = SiteLocation.objects.get_current()
        self.assertEqual('max', sl.tier_name)

        c = self._log_in_as_superuser()
        response = c.get(reverse('localtv_admin_tier'))
        self.assertFalse(response.context['offer_free_trial'])

        # This should be False. The idea is that we cancel the old, trial-based
        # subscription. We will create a new subscription so that it can start
        # immediately.
        self.assertFalse(response.context['can_modify_mapping']['premium'])

        self._run_method_from_ipn_integration_test_case('upgrade_between_paid_tiers')

        ti = TierInfo.objects.get_current()
        self.assertNotEqual(old_profile, ti.current_paypal_profile_id)
        self.assertEqual([], mail.outbox)
        self.assertFalse(ti.in_free_trial)

    def test_downgrade_to_paid_not_during_a_trial(self):
        # Let's say the user started at 'max' and free trial, and then switched down to 'premium'
        # which ended the trial.
        self.test_downgrade_to_paid_during_a_trial()

        # Sanity-check the free trial state.
        ti = TierInfo.objects.get_current()
        self.assertFalse(ti.free_trial_available)
        self.assertFalse(ti.in_free_trial)
        self.assertTrue(ti.current_paypal_profile_id)
        old_profile = ti.current_paypal_profile_id

        # We are in 'premium'. Let's consider what happens when
        # we want to downgrade to 'plus'
        sl = SiteLocation.objects.get_current()
        self.assertEqual('premium', sl.tier_name)

        c = self._log_in_as_superuser()
        response = c.get(reverse('localtv_admin_tier'))
        self.assertFalse(response.context['offer_free_trial'])

        # This should be False. There is no reason to provide extra payment data; we're just
        # going to modify the subscription amount.
        self.assertFalse(response.context['upgrade_extra_payments']['plus'])

        # This should be True. This is a simple PayPal subscription modification case.
        self.assertTrue(response.context['can_modify_mapping']['plus'])

        # Go to the Downgrade Confirm page
        response = c.post(reverse('localtv_admin_downgrade_confirm'),
                          {'target_tier_name': 'plus'})

        self.assertTrue(response.context['can_modify'])
        self.assertTrue('"modify" value="1"' in response.content)

        self._run_method_from_ipn_integration_test_case('submit_ipn_subscription_modify', str(PLUS_COST), old_profile)

        ti = TierInfo.objects.get_current()
        self.assertEqual(old_profile, ti.current_paypal_profile_id)
        self.assertEqual([], mail.outbox)
        self.assertFalse(ti.in_free_trial)
        self.assertEqual('plus', SiteLocation.objects.get_current().tier_name)

class TestFreeTrial(BaseTestCase):

    @mock.patch('localtv.admin.tiers._start_free_trial_for_real')
    def test_does_nothing_if_already_in_free_trial(self, m):
        # If we are already in a free trial, then we refuse to continue:
        ti = TierInfo.objects.get_current()
        ti.in_free_trial = True
        ti.save()
        localtv.admin.tiers._start_free_trial_unconfirmed('basic')
        self.assertFalse(m.called)
