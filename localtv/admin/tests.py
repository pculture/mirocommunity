import datetime

from django.core.files.base import File
from django.core.paginator import Page
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.db.models import Q
from django.test.client import Client
from django.utils.encoding import force_unicode

from localtv.admin import forms as admin_forms
from localtv.tests import BaseTestCase
from localtv import models
from localtv import util

import vidscraper

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
                if isinstance(field, admin_forms.SourceChoiceField):
                    if data is not None:
                        data = '%s-%s' % (data.__class__.__name__.lower(),
                                          data.pk)
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

    fixtures = BaseTestCase.fixtures + ['videos']

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
        self.assertEquals(response.template[0].name,
                          'localtv/admin/approve_reject_table.html')
        self.assertIsInstance(response.context['current_video'],
                              models.Video)
        self.assertIsInstance(response.context['page_obj'],
                              Page)
        video_list = response.context['video_list']
        self.assertEquals(video_list[0], response.context['current_video'])
        self.assertEquals(len(video_list), 10)

    def test_GET_with_page(self):
        """
        A GET request ot the approve/reject view with a 'page' GET argument
        should return that page of the videos to be approved/rejected.  The
        first page is the 10 oldest videos, the second page is the next 10,
        etc.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED).order_by(
            'when_submitted', 'when_published')
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        page1_response = c.get(self.url,
                               {'page': '1'})
        self.assertEquals(list(response.context['video_list']),
                          list(page1_response.context['video_list']))
        self.assertEquals(list(page1_response.context['video_list']),
                          list(unapproved_videos[:10]))
        page2_response = c.get(self.url,
                               {'page': '2'})
        self.assertNotEquals(page1_response, page2_response)
        self.assertEquals(list(page2_response.context['video_list']),
                          list(unapproved_videos[10:20]))
        page3_response = c.get(self.url,
                               {'page': '3'}) # doesn't exist, should return
                                              # page 2
        self.assertEquals(list(page2_response.context['video_list']),
                          list(page3_response.context['video_list']))

    def test_GET_preview(self):
        """
        A GET request to the preview_video view should render the
        'localtv/admin/video_preview.html' template and have a
        'current_video' in the context.  The current_video should be the video
        with the primary key passed in as GET['video_id'].
        """
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)[0]
        url = reverse('localtv_admin_preview_video')
        self.assertRequiresAuthentication(url, {'video_id': str(video.pk)})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url,
                         {'video_id': str(video.pk)})
        self.assertEquals(response.template[0].name,
                          'localtv/admin/video_preview.html')
        self.assertEquals(response.context['current_video'],
                          video)

    def test_GET_approve(self):
        """
        A GET request to the approve_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].
        """
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)[0]
        url = reverse('localtv_admin_approve_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        video = models.Video.objects.get(pk=video.pk) # reload
        self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
        self.assertTrue(video.when_approved is not None)
        self.assertTrue(video.last_featured is None)

    def test_GET_approve_with_feature(self):
        """
        A GET request to the approve_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].  When 'feature' is present in the GET arguments, the
        video should also be featured.
        """
        # XXX why do we have this function
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)[0]
        url = reverse('localtv_admin_approve_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk,
                                                'feature': 'yes'})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk),
                               'feature': 'yes'},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        video = models.Video.objects.get(pk=video.pk) # reload
        self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
        self.assertTrue(video.when_approved is not None)
        self.assertTrue(video.last_featured is not None)

    def test_GET_reject(self):
        """
        A GET request to the reject_video view should reject the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].
        """
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)[0]
        url = reverse('localtv_admin_reject_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        video = models.Video.objects.get(pk=video.pk) # reload
        self.assertEquals(video.status, models.VIDEO_STATUS_REJECTED)
        self.assertTrue(video.last_featured is None)

    def test_GET_feature(self):
        """
        A GET request to the feature_video view should approve the video and
        redirect back to the referrer.  The video should be specified by
        GET['video_id'].  If the video is unapproved, it should become
        approved.
        """
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)[0]
        url = reverse('localtv_admin_feature_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        video = models.Video.objects.get(pk=video.pk) # reload
        self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
        self.assertTrue(video.when_approved is not None)
        self.assertTrue(video.last_featured is not None)

    def test_GET_unfeature(self):
        """
        A GET request to the unfeature_video view should unfeature the video
        and redirect back to the referrer.  The video should be specified by
        GET['video_id'].  The video status is not affected.
        """
        video = models.Video.objects.filter(
            status=models.VIDEO_STATUS_ACTIVE).exclude(
            last_featured=None)[0]

        url = reverse('localtv_admin_unfeature_video')
        self.assertRequiresAuthentication(url, {'video_id': video.pk})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'video_id': str(video.pk)},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        video = models.Video.objects.get(pk=video.pk) # reload
        self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
        self.assertTrue(video.last_featured is None)

    def test_GET_reject_all(self):
        """
        A GET request to the reject_all view should reject all the videos on
        the given page and redirect back to the referrer.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)
        page2_videos = unapproved_videos[10:20]

        url = reverse('localtv_admin_reject_all')
        self.assertRequiresAuthentication(url, {'page': 2})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'page': 2},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        for video in page2_videos:
            self.assertEquals(video.status, models.VIDEO_STATUS_REJECTED)

    def test_GET_approve_all(self):
        """
        A GET request to the reject_all view should approve all the videos on
        the given page and redirect back to the referrer.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)
        page2_videos = unapproved_videos[10:20]

        url = reverse('localtv_admin_approve_all')
        self.assertRequiresAuthentication(url, {'page': 2})

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'page': 2},
                         HTTP_REFERER='http://referer.com')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://referer.com')

        for video in page2_videos:
            self.assertEquals(video.status, models.VIDEO_STATUS_ACTIVE)
            self.assertTrue(video.when_approved is not None)


    def test_GET_clear_all(self):
        """
        A GET request to the clear_all view should render the
        'localtv/admin/clear_confirm.html' and have a 'videos' variable
        in the context which is a list of all the unapproved videos.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)
        unapproved_videos_count = unapproved_videos.count()

        url = reverse('localtv_admin_clear_all')
        self.assertRequiresAuthentication(url)

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/admin/clear_confirm.html')
        self.assertEquals(list(response.context['videos']),
                          list(unapproved_videos))

        # nothing was rejected
        self.assertEquals(models.Video.objects.filter(
                status=models.VIDEO_STATUS_UNAPPROVED).count(),
                          unapproved_videos_count)

    def test_POST_clear_all_failure(self):
        """
        A POST request to the clear_all view without POST['confirm'] = 'yes'
        should render the 'localtv/admin/clear_confirm.html' template
        and have a 'videos' variable in the context which is a list of all the
        unapproved videos.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)
        unapproved_videos_count = unapproved_videos.count()

        url = reverse('localtv_admin_clear_all')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/admin/clear_confirm.html')
        self.assertEquals(list(response.context['videos']),
                          list(unapproved_videos))

        # nothing was rejected
        self.assertEquals(models.Video.objects.filter(
                status=models.VIDEO_STATUS_UNAPPROVED).count(),
                          unapproved_videos_count)

    def test_POST_clear_all_succeed(self):
        """
        A POST request to the clear_all view with POST['confirm'] = 'yes'
        should reject all the videos and redirect to the approve_reject view.
        """
        unapproved_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_UNAPPROVED)
        unapproved_videos_count = unapproved_videos.count()

        rejected_videos = models.Video.objects.filter(
            status=models.VIDEO_STATUS_REJECTED)
        rejected_videos_count = rejected_videos.count()

        url = reverse('localtv_admin_clear_all')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url, {'confirm': 'yes'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_admin_approve_reject')))

        # all the unapproved videos are now rejected
        self.assertEquals(models.Video.objects.filter(
                status=models.VIDEO_STATUS_REJECTED).count(),
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
        self.assertEquals(response.template[0].name,
                          'localtv/admin/manage_sources.html')
        self.assertTrue('add_feed_form' in response.context[0])
        self.assertTrue('page' in response.context[0])
        self.assertTrue('headers' in response.context[0])
        self.assertEquals(response.context[0]['search_string'], '')
        self.assertTrue(response.context[0]['source_filter'] is None)
        self.assertEquals(response.context[0]['categories'].model,
                          models.Category)
        self.assertTrue(response.context[0]['users'].model, User)
        self.assertTrue('successful' in response.context[0])
        self.assertTrue('formset' in response.context[0])

        page = response.context['page']
        self.assertEquals(len(page.object_list), 15)
        self.assertEquals(list(sorted(page.object_list,
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
        self.assertEquals(list(sorted(page.object_list,
                                      key=lambda x:unicode(x).lower())),
                          page.object_list)

        # reversed name
        response = c.get(self.url, {'sort': '-name__lower'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:unicode(x).lower())),
                          page.object_list)

        # auto approve
        response = c.get(self.url, {'sort': 'auto_approve'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      key=lambda x:x.auto_approve)),
                          page.object_list)

        # reversed auto_approve
        response = c.get(self.url, {'sort': '-auto_approve'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:x.auto_approve)),
                          page.object_list)

        # type (feed, search, user)
        response = c.get(self.url, {'sort': 'type'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      key=lambda x:x.source_type().lower())),
                          page.object_list)

        # reversed type (user, search, feed)
        response = c.get(self.url, {'sort': '-type'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
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
        self.assertEquals(
            list(page.object_list),
            list(models.SavedSearch.objects.extra({
                        'name__lower': 'LOWER(query_string)'}).order_by(
                    'name__lower')[:10]))

        # feed filter (ignores feeds that represent video service users)
        response = c.get(self.url, {'filter': 'feed'})
        page = response.context['page']
        self.assertEquals(len(page.object_list), 4)
        for feed in page.object_list:
            self.assertTrue(feed.video_service() is None)

        # user filter (only includes feeds that represent video service users)
        response = c.get(self.url, {'filter': 'user'})
        page = response.context['page']
        self.assertEquals(len(page.object_list), 6)
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
        self.assertEquals(len(POST_response.context['formset'].errors[0]), 2)
        self.assertEquals(len(POST_response.context['formset'].errors[1]), 1)

        # make sure the data hasn't changed
        self.assertEquals(POST_data,
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

        POST_data.update({
                'form-0-name': 'new name!',
                'form-0-feed_url': 'http://pculture.org/',
                'form-0-webpage': 'http://getmiro.com/',
                'form-1-query_string': 'localtv'})

        POST_response = c.post(self.url, POST_data,
                               follow=True)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEquals(POST_response.redirect_chain,
                          [('http://%s%s?successful' % (
                        self.site_location.site.domain,
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

        # make sure the data has been updated
        feed = models.Feed.objects.get(pk=POST_data['form-0-id'].split('-')[1])
        self.assertEquals(feed.name, POST_data['form-0-name'])
        self.assertEquals(feed.feed_url, POST_data['form-0-feed_url'])
        self.assertEquals(feed.webpage, POST_data['form-0-webpage'])

        search = models.SavedSearch.objects.get(
            pk=POST_data['form-1-id'].split('-')[1])
        self.assertEquals(search.query_string,
                          POST_data['form-1-query_string'])


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
        self.assertEquals(POST_response.redirect_chain,
                          [('http://%s%s?page=2&successful' % (
                        self.site_location.site.domain,
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

    def test_POST_delete(self):
        """
        A POST request to the manage sources view with a valid formset and a
        DELETE value for a source should remove that source along with all of
        its videos.`
        """
        feed = models.Feed.objects.get(pk=3)
        saved_search = models.SavedSearch.objects.get(pk=8)

        for v in models.Video.objects.all()[:5]:
            v.feed = feed
            v.save()

        for v in models.Video.objects.all()[5:10]:
            v.search = saved_search
            v.save()

        video_count = models.Video.objects.count()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)
        POST_data['form-0-DELETE'] = 'yes'
        POST_data['form-1-DELETE'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        self.assertEquals(
            models.Feed.objects.filter(pk=3).count(), # form 0
            0)

        self.assertEquals(
            models.SavedSearch.objects.filter(pk=8).count(), # form 1
            0)

        # make sure the 10 videos got removed
        self.assertEquals(models.Video.objects.count(),
                          video_count - 10)

    def test_POST_bulk_edit(self):
        """
        A POST request to the manage_sources view with a valid formset and the
        extra form filled out should update any source with the bulk option
        checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['form-15-auto_categories'] = [1, 2]
        POST_data['form-15-auto_authors'] = [1, 2]
        POST_data['form-15-auto_approve'] = 'yes'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        feed = models.Feed.objects.get(pk=3) # form 0
        saved_search = models.SavedSearch.objects.get(pk=8) # form 1

        self.assertEquals(feed.auto_approve, True)
        self.assertEquals(saved_search.auto_approve, True)
        self.assertEquals(
            set(feed.auto_categories.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEquals(
            set(saved_search.auto_categories.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEquals(
            set(feed.auto_authors.values_list('pk', flat=True)),
            set([1, 2]))
        self.assertEquals(
            set(saved_search.auto_authors.values_list('pk', flat=True)),
            set([1, 2]))

    def test_POST_bulk_delete(self):
        """
        A POST request to the manage_sources view with a valid formset and a
        POST['bulk_action'] of 'remove' should remove the videos with the bulk
        option checked.
        """
        feed = models.Feed.objects.get(pk=3)
        saved_search = models.SavedSearch.objects.get(pk=8)

        for v in models.Video.objects.all()[:5]:
            v.feed = feed
            v.save()

        for v in models.Video.objects.all()[5:10]:
            v.search = saved_search
            v.save()

        video_count = models.Video.objects.count()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['bulk_action'] = 'remove'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        self.assertEquals(
            models.Feed.objects.filter(pk=3).count(), # form 0
            0)

        self.assertEquals(
            models.SavedSearch.objects.filter(pk=8).count(), # form 1
            0)

        # make sure the 10 videos got removed
        self.assertEquals(models.Video.objects.count(),
                          video_count - 10)

    def test_POST_switching_categories_authors(self):
        """
        A POST request to the manage_sources view with a valid formset that
        includes changed categories or authors, videos that had the old
        categories/authors should be updated to the new values.
        """
        feed = models.Feed.objects.get(pk=3)
        saved_search = models.SavedSearch.objects.get(pk=8)
        category = models.Category.objects.get(pk=1)
        user = User.objects.get(pk=1)
        category2 = models.Category.objects.get(pk=2)
        user2 = User.objects.get(pk=2)

        for v in models.Video.objects.order_by('pk')[:3]:
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

        for v in models.Video.objects.order_by('pk')[3:6]:
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
            POST_data['form-%i-bulk'% i] = 'yes'
        POST_data['form-15-auto_categories'] = [category2.pk]
        POST_data['form-15-auto_authors'] = [user2.pk]

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        for v in models.Video.objects.order_by('pk')[:3]:
            self.assertEquals(v.feed, feed)
            if v.pk == 1:
                # nothing changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user]))
            elif v.pk == 2:
                # user changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user2]))
            elif v.pk == 3:
                # category changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category2]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user]))
            else:
                self.fail('invalid feed video pk: %i' % v.pk)

        for v in models.Video.objects.order_by('pk')[3:6]:
            self.assertEquals(v.search, saved_search)
            if v.pk == 4:
                # nothing changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user]))
            elif v.pk == 5:
                # user changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category]))
                self.assertEquals(
                    set(v.authors.all()),
                    set([user2]))
            elif v.pk == 6:
                # category changed
                self.assertEquals(
                    set(v.categories.all()),
                    set([category2]))
                self.assertEquals(
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

    def test_authentication_done(self):
        """
        The localtv_admin_feed_add_done view should require administration
        priviledges.
        """
        url = reverse('localtv_admin_feed_add_done', args=[1])
        self.assertRequiresAuthentication(url)

        self.assertRequiresAuthentication(url,
                                          username='user', password='password')

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
        self.assertEquals(response.template[2].name,
                          'localtv/admin/add_feed.html')
        self.assertTrue(response.context[2]['form'].instance.feed_url,
                        self.feed_url)
        self.assertEquals(response.context[2]['video_count'], 1)

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
        self.assertEquals(response.template[2].name,
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
        self.assertEquals(response.template[2].name,
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
        self.assertEquals(response.template[0].name,
                          'localtv/admin/add_feed.html')
        self.assertTrue(response.context[0]['form'].instance.feed_url,
                        self.feed_url)
        self.assertFalse(response.context[0]['form'].is_valid())
        self.assertEquals(response.context[0]['video_count'], 1)

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
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_admin_manage_page')))

        self.assertEquals(models.Feed.objects.count(), 0)

    def test_POST_succeed(self):
        """
        A POST request to the add_feed view with a valid form should redirect
        the user to the localtv_admin_add_feed_done view.

        A Feed object should also be created, but not have any items.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(self.url + "?feed_url=%s" % self.feed_url,
                          {'feed_url': self.feed_url,
                           'auto_approve': 'yes'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_admin_feed_add_done', args=[1])))

        feed = models.Feed.objects.get()
        self.assertEquals(feed.name, 'Valid Feed with Relative Links')
        self.assertEquals(feed.feed_url, self.feed_url)
        self.assertTrue(feed.auto_approve)

    def test_GET_done(self):
        """
        A GET request to the add_feed_done view should import videos from the
        given feed.  It should also render the
        'localtv/admin/feed_done.html' template and have a 'feed'
        variable in the context pointing to the Feed object.
        """
        c = Client()
        c.login(username='admin', password='admin')
        c.post(self.url + "?feed_url=%s" % self.feed_url,
               {'feed_url': self.feed_url,
                'auto_approve': 'yes'})

        response = c.get(reverse('localtv_admin_feed_add_done', args=[1]))
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[2].name,
                          'localtv/admin/feed_done.html')
        feed = models.Feed.objects.get()
        self.assertEquals(response.context[2]['feed'], feed)
        self.assertEquals(feed.video_set.count(), 1)

        video = feed.video_set.all()[0]
        self.assertEquals(video.status,
                          models.VIDEO_STATUS_ACTIVE)
        self.assertEquals(video.thumbnail_url,
                          ('http://participatoryculture.org/feeds_test/'
                           'mike_tv_drawing_cropped.jpg'))
        self.assertEquals(video.file_url,
                          ('http://participatoryculture.org/feeds_test/'
                           'py1.mov'))
        self.assertEquals(video.file_url_mimetype, 'video/quicktime')
        self.assertEquals(video.file_url_length, 842)

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

        feed = models.Feed.objects.get()
        user = User.objects.get(username='mphtower')
        self.assertEquals(feed.name, 'mphtower')

        self.assertFalse(user.has_usable_password())
        self.assertEquals(user.email, '')
        self.assertEquals(user.get_profile().website,
                          'http://www.youtube.com/profile_videos?'
                          'user=mphtower')
        self.assertEquals(list(feed.auto_authors.all()),
                          [user])

    def test_GET_reuses_existing_user(self):
        """
        When creating a feed from a feed for a user on a video servers, if a
        User already exists with the given username, it should be used instead
        of creating a new object.
        """
        user = User.objects.create_user('mphtower', 'mph@tower.com',
                                        'password')
        models.Profile.objects.create(user=user,
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
        self.assertEquals(user.email, 'mph@tower.com')
        self.assertEquals(user.get_profile().website,
                          'http://www.mphtower.com/')

        feed = models.Feed.objects.get()
        self.assertEquals(list(feed.auto_authors.all()),
                          [user])

    def test_GET_auto_approve(self):
        """
        A GET request to the feed_auto_approve view should set the auto_approve
        bit on the feed specified in the URL and redirect back to the referrer.
        It should also require the user to be an administrator.
        """
        feed = models.Feed.objects.create(site=self.site_location.site,
                                          name='name',
                                          feed_url='feed_url',
                                          auto_approve=False,
                                          last_updated=datetime.datetime.now(),
                                          status=models.FEED_STATUS_ACTIVE)
        url = reverse('localtv_admin_feed_auto_approve', args=(feed.pk,))
        self.assertRequiresAuthentication(url)
        self.assertRequiresAuthentication(url,
                                          username='user',
                                          password='password')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url,
                         HTTP_REFERER='http://www.google.com/')
        self.assertEquals(feed.auto_approve, False)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'], 'http://www.google.com/')

    def test_GET_auto_approve_disable(self):
        """
        A GET request to the feed_auto_approve view with GET['disable'] set
        should remove the auto_approve bit on the feed specified in the URL and
        redirect back to the referrer.
        """
        feed = models.Feed.objects.create(site=self.site_location.site,
                                          name='name',
                                          feed_url='feed_url',
                                          auto_approve=True,
                                          last_updated=datetime.datetime.now(),
                                          status=models.FEED_STATUS_ACTIVE)
        url = reverse('localtv_admin_feed_auto_approve', args=(feed.pk,))

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(url, {'disable': 'yes'},
                         HTTP_REFERER='http://www.google.com/')
        self.assertEquals(feed.auto_approve, True)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'], 'http://www.google.com/')


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
        self.assertEquals(response.template[0].name,
                          'localtv/admin/livesearch_table.html')
        self.assertTrue('current_video' in response.context[0])
        self.assertTrue('page_obj' in response.context[0])
        self.assertTrue('query_string' in response.context[0])
        self.assertTrue('order_by' in response.context[0])
        self.assertTrue('is_saved_search' in response.context[0])

    def test_GET_query(self):
        """
        A GET request to the livesearch view and GET['query'] argument should
        list some videos that match the query.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'query': 'search string'})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[2].name,
                          'localtv/admin/livesearch_table.html')
        self.assertIsInstance(response.context[2]['current_video'],
                              util.MetasearchVideo)
        self.assertEquals(response.context[2]['page_obj'].number, 1)
        self.assertEquals(len(response.context[2]['page_obj'].object_list), 10)
        self.assertEquals(response.context[2]['query_string'], 'search string')
        self.assertEquals(response.context[2]['order_by'], 'latest')
        self.assertEquals(response.context[2]['is_saved_search'], False)

    def test_GET_query_pagination(self):
        """
        A GET request to the livesearch view with GET['query'] and GET['page']
        arguments should return another page of results.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'query': 'search string'})
        self.assertEquals(response.context[2]['page_obj'].number, 1)
        self.assertEquals(len(response.context[2]['page_obj'].object_list), 10)

        response2 = c.get(self.url,
                         {'query': 'search string',
                          'page': '2'})
        self.assertEquals(response2.context[2]['page_obj'].number, 2)
        self.assertEquals(len(response2.context[2]['page_obj'].object_list),
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
        c.login(username='admin', password='admin')
        response = c.get(self.url,
                         {'query': 'search string'})
        metasearch_video = response.context[2]['page_obj'].object_list[0]
        metasearch_video2 = response.context[2]['page_obj'].object_list[1]

        response = c.get(reverse('localtv_admin_search_video_approve'),
                         {'query': 'search string',
                          'video_id': metasearch_video.id},
                         HTTP_REFERER="http://www.getmiro.com/")
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'], "http://www.getmiro.com/")

        v = models.Video.objects.get()
        self.assertEquals(v.site, self.site_location.site)
        self.assertEquals(v.name, metasearch_video.name)
        self.assertEquals(
            v.description,
            vidscraper.auto_scrape(v.website_url,
                                   fields=['description'])['description'])
        self.assertEquals(v.file_url, metasearch_video.file_url)
        self.assertEquals(v.embed_code, metasearch_video.embed_code)
        self.assertTrue(v.last_featured is None)

        user = User.objects.get(username=v.video_service_user)
        self.assertFalse(user.has_usable_password())
        self.assertEquals(user.get_profile().website,
                          v.video_service_url)
        self.assertEquals(list(v.authors.all()), [user])

        response = c.get(self.url,
                         {'query': 'search string'})
        self.assertEquals(response.context[2]['page_obj'].object_list[0].id,
                          metasearch_video2.id)

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
                         {'query': 'search string'})
        metasearch_video = response.context[2]['page_obj'].object_list[0]

        response = c.get(reverse('localtv_admin_search_video_approve'),
                         {'query': 'search string',
                          'feature': 'yes',
                          'video_id': metasearch_video.id},
                         HTTP_REFERER="http://www.getmiro.com/")
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'], "http://www.getmiro.com/")

        v = models.Video.objects.get()
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
                         {'query': 'search string'})
        metasearch_video = response.context[2]['page_obj'].object_list[0]

        response = c.get(reverse('localtv_admin_search_video_display'),
                         {'query': 'search string',
                          'video_id': metasearch_video.id})
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/admin/video_preview.html')
        self.assertEquals(response.context[0]['current_video'].id,
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
                         {'query': 'search string'},
                         HTTP_REFERER='http://www.getmiro.com/')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'], 'http://www.getmiro.com/')

        saved_search = models.SavedSearch.objects.get()
        self.assertEquals(saved_search.query_string, 'search string')
        self.assertEquals(saved_search.site, self.site_location.site)
        self.assertEquals(saved_search.user.username, 'admin')

        response = c.get(self.url,
                         {'query': 'search string'})
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
        saved_search = models.SavedSearch.objects.create(
            site=self.site_location.site,
            query_string='search string')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(reverse('localtv_admin_search_auto_approve',
                                 args=[saved_search.pk]),
                         HTTP_REFERER='http://www.getmiro.com/')
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://www.getmiro.com/')

        saved_search = models.SavedSearch.objects.get(pk=saved_search.pk)
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
        saved_search = models.SavedSearch.objects.create(
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
        self.assertEquals(response['Location'],
                          'http://www.getmiro.com/')

        saved_search = models.SavedSearch.objects.get(pk=saved_search.pk)
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
        self.assertEquals(response.template[0].name,
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
        self.assertEquals(response.template[0].name,
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
        self.assertEquals(response.template[0].name,
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
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@testserver.local',
            'role': 'user',
            'description': 'A New User',
            'logo': file(self._data_file('logo.png'))
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        new = User.objects.order_by('-id')[0]
        profile = new.get_profile()
        for key, value in POST_data.items():
            if key == 'submit':
                pass
            elif key == 'role':
                new_site_location = models.SiteLocation.objects.get()
                self.assertFalse(new_site_location.user_is_admin(new))
            elif key == 'logo':
                profile.logo.open()
                value.seek(0)
                self.assertEquals(profile.logo.read(), value.read())
            elif key == 'description':
                self.assertEquals(profile.description, value)
            else:
                self.assertEquals(getattr(new, key), value)

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
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@testserver.local',
            'role': 'admin',
            'description': 'A New User',
            'logo': file(self._data_file('logo.png')),
            'password_f': 'new_password',
            'password_f2': 'new_password'
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        new = User.objects.order_by('-id')[0]
        profile = new.get_profile()
        for key, value in POST_data.items():
            if key in ('submit', 'password_f', 'password_f2'):
                pass
            elif key == 'role':
                new_site_location = models.SiteLocation.objects.get()
                self.assertTrue(new_site_location.user_is_admin(new))
            elif key == 'logo':
                profile.logo.open()
                value.seek(0)
                self.assertEquals(profile.logo.read(), value.read())
            elif key == 'description':
                self.assertEquals(profile.description, value)
            else:
                self.assertEquals(getattr(new, key), value)

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
        models.Profile.objects.create(
            user=user,
            logo=File(file(self._data_file('logo.png'))),
            description='Some description about the user')

        old_users = User.objects.values()
        old_profiles = models.Profile.objects.values()

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']

        POST_response = c.post(self.url, self._POST_data_from_formset(
                formset,
                submit='Save'))
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        for old, new in zip(old_users, User.objects.values()):
            self.assertEquals(old, new)
        for old, new in zip(old_profiles, models.Profile.objects.values()):
            self.assertEquals(old, new)

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
        POST_data['form-0-first_name'] = 'New First'
        POST_data['form-0-last_name'] = 'New Last'
        POST_data['form-0-role'] = 'user'
        POST_data['form-1-logo'] = file(self._data_file('logo.png'))
        POST_data['form-1-description'] = 'Superuser Description'
        POST_data['form-2-username'] = 'new_admin'
        POST_data['form-2-role'] = 'admin'
        POST_data['form-2-password_f'] = 'new_admin'
        POST_data['form-2-password_f2'] = 'new_admin'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        self.assertEquals(User.objects.count(), 3) # no one got added

        new_admin = User.objects.get(username='new_admin')
        self.assertEquals(new_admin.pk, 1)
        self.assertTrue(self.site_location.user_is_admin(new_admin))
        self.assertTrue(new_admin.check_password('new_admin'))

        superuser = User.objects.get(username='superuser')
        self.assertEquals(superuser.pk, 2)
        self.assertEquals(superuser.is_superuser, True)
        self.assertFalse(superuser in self.site_location.admins.all())
        self.assertTrue(superuser.check_password('superuser'))
        profile = superuser.get_profile()
        self.assertTrue(profile.logo.name.endswith('logo.png'))
        self.assertEquals(profile.description, 'Superuser Description')

        old_admin = User.objects.get(username='admin')
        self.assertEquals(old_admin.pk, 3)
        self.assertEquals(old_admin.first_name, 'New First')
        self.assertEquals(old_admin.last_name, 'New Last')
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
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        self.assertEquals(User.objects.count(), 2) # one user got removed

        self.assertEquals(User.objects.filter(username='user').count(), 0)
        self.assertEquals(User.objects.filter(is_superuser=True).count(), 1)


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
        self.assertEquals(response.template[0].name,
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
        self.assertEquals(response.template[0].name,
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
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
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
        self.assertEquals(response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        new = models.Category.objects.order_by('-id')[0]

        self.assertEquals(new.site, self.site_location.site)

        for key, value in POST_data.items():
            if key == 'submit':
                pass
            elif key == 'logo':
                new.logo.open()
                value.seek(0)
                self.assertEquals(new.logo.read(), value.read())
            elif key == 'parent':
                self.assertEquals(new.parent.pk, value)
            else:
                self.assertEquals(getattr(new, key), value)

    def test_POST_save_no_changes(self):
        """
        A POST to the categoriess view with a POST['submit'] of 'Save' and a
        successful formset should update the category data.  The default values
        of the formset should not change the values of any of the Categorys.
        """
        c = Client()
        c.login(username="admin", password="admin")

        old_categories = models.Category.objects.values()

        GET_response = c.get(self.url)
        formset = GET_response.context['formset']

        POST_response = c.post(self.url, self._POST_data_from_formset(
                formset,
                submit='Save'))

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        for old, new in zip(old_categories, models.Category.objects.values()):
            self.assertEquals(old, new)

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
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        self.assertEquals(models.Category.objects.count(), 5) # no one got
                                                              # added

        new_slug = models.Category.objects.get(slug='newslug')
        self.assertEquals(new_slug.pk, 5)
        self.assertEquals(new_slug.name, 'New Name')

        new_logo = models.Category.objects.get(slug='miro')
        new_logo.logo.open()
        self.assertEquals(new_logo.logo.read(),
                          file(self._data_file('logo.png')).read())
        self.assertEquals(new_logo.description, 'New Description')

        new_parent = models.Category.objects.get(slug='linux')
        self.assertEquals(new_parent.parent.pk, 5)

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
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        # three categories got removed
        self.assertEquals(models.Category.objects.count(), 2)

        # both of the other categories got their parents reassigned to None
        self.assertEquals(models.Category.objects.filter(parent=None).count(),
                          2)

    def test_POST_bulk_delete(self):
        """
        A POST request to the categories view with a valid formset and a
        POST['action'] of 'delete' should reject the videos with the bulk
        option checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['form-2-bulk'] = 'yes'
        POST_data['submit'] = 'Apply'
        POST_data['action'] = 'delete'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))


        # three categories got removed
        self.assertEquals(models.Category.objects.count(), 2)

        # both of the other categories got their parents reassigned to None
        self.assertEquals(models.Category.objects.filter(parent=None).count(),
                          2)


# -----------------------------------------------------------------------------
# Bulk edit administration tests
# -----------------------------------------------------------------------------


class BulkEditAdministrationTestCase(AdministrationBaseTestCase):

    fixtures = AdministrationBaseTestCase.fixtures + [
        'feeds', 'videos', 'categories']

    url = reverse('localtv_admin_bulk_edit')

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
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)

        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/admin/bulk_edit.html')
        self.assertEquals(response.context[0]['page'].number, 1)
        self.assertTrue('formset' in response.context[0])
        self.assertEquals(
            [form.instance for form in
             response.context[0]['formset'].initial_forms],
            list(models.Video.objects.filter(
                    status=models.VIDEO_STATUS_ACTIVE).order_by(
                    'name')[:50]))
        self.assertTrue('headers' in response.context[0])
        self.assertEquals(list(response.context[0]['categories']),
                          list(models.Category.objects.filter(
                site=self.site_location.site)))
        self.assertEquals(list(response.context[0]['users']),
                          list(User.objects.all()))


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
        self.assertEquals(list(sorted(page.object_list,
                                      key=lambda x:unicode(x).lower())),
                          list(page.object_list))

        # reversed name
        response = c.get(self.url, {'sort': '-name'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:unicode(x).lower())),
                          list(page.object_list))

        # auto approve
        response = c.get(self.url, {'sort': 'when_published'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      key=lambda x:x.when_published)),
                          list(page.object_list))

        # reversed auto_approve
        response = c.get(self.url, {'sort': '-when_published'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      reverse=True,
                                      key=lambda x:x.when_published)),
                          list(page.object_list))

        # source (feed, search, user)
        response = c.get(self.url, {'sort': 'source'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
                                      key=lambda x:x.source_type())),
                          list(page.object_list))

        # reversed source (user, search, feed)
        response = c.get(self.url, {'sort': '-source'})
        page = response.context['page']
        self.assertEquals(list(sorted(page.object_list,
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
        self.assertEquals(list(response.context['page'].object_list),
                          list(models.Video.objects.filter(
                    categories=3,
                    status=models.VIDEO_STATUS_ACTIVE,
                    ).order_by('name')))

    def test_GET_filter_authors(self):
        """
        A GET request with an 'author' key in the GET request should filter the
        results to only include videos with that author.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'author': '3'})
        self.assertEquals(list(response.context['page'].object_list),
                          list(models.Video.objects.filter(
                    authors=3,
                    status=models.VIDEO_STATUS_ACTIVE,
                    ).order_by('name')))

    def test_GET_filter_featured(self):
        """
        A GET request with an 'featured' key in the GET request should restrict
        the results to only those videos that have been featured.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'featured': 'yes'})
        self.assertEquals(list(response.context['page'].object_list),
                          list(models.Video.objects.filter(
                    status=models.VIDEO_STATUS_ACTIVE,
                    ).exclude(last_featured=None).order_by('name')))

    def test_GET_search(self):
        """
        A GET request with a 'q' key in the GET request should search the
        videos for that string.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url, {'q': 'blend'})
        self.assertEquals(list(response.context['page'].object_list),
                          list(models.Video.objects.filter(
                    Q(name__icontains="blend") |
                    Q(description__icontains="blend") |
                    Q(feed__name__icontains="blend"),
                    status=models.VIDEO_STATUS_ACTIVE,
                    ).order_by('name')))

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
        self.assertEquals(len(POST_response.context['formset'].errors[0]), 1)
        self.assertEquals(len(POST_response.context['formset'].errors[1]), 1)

        # make sure the data hasn't changed
        self.assertEquals(POST_data,
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
                'form-1-description': 'localtv',
                'form-1-embed_code': 'new embed code'
                })

        POST_response = c.post(self.url, POST_data,
                               follow=True)
        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEquals(POST_response.redirect_chain,
                          [('http://%s%s?successful' % (
                        self.site_location.site.domain,
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

        # make sure the data has been updated
        video1 = models.Video.objects.get(pk=POST_data['form-0-id'])
        self.assertEquals(video1.name, POST_data['form-0-name'])
        self.assertEquals(video1.file_url, POST_data['form-0-file_url'])
        self.assertEquals(video1.embed_code, POST_data['form-0-embed_code'])

        video2 = models.Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertEquals(video2.description,
                          POST_data['form-1-description'])
        self.assertEquals(video2.embed_code,
                          POST_data['form-1-embed_code'])

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
        self.assertEquals(POST_response.redirect_chain,
                          [('http://%s%s?page=2&successful' % (
                        self.site_location.site.domain,
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
        self.assertEquals(POST_response.redirect_chain,
                          [('http://%s%s?page=2&successful' % (
                        self.site_location.site.domain,
                        self.url), 302)])
        self.assertFalse(POST_response.context['formset'].is_bound)

    def test_POST_delete(self):
        """
        A POST request to the manage sources view with a valid formset and a
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
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        # make sure the data has been updated
        video1 = models.Video.objects.get(pk=POST_data['form-0-id'])
        self.assertEquals(video1.status, models.VIDEO_STATUS_REJECTED)

        video2 = models.Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertEquals(video2.status, models.VIDEO_STATUS_REJECTED),

    def test_POST_bulk_edit(self):
        """
        A POST request to the bulk_edit view with a valid formset and the
        extra form filled out should update any source with the bulk option
        checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['form-%i-categories' % (len(formset.forms) - 1)] = [1, 2]
        POST_data['form-%i-authors' % (len(formset.forms) - 1)] = [1, 2]
        POST_data['form-%i-tags' % (len(formset.forms) - 1)] = 'tag3, tag4'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        # make sure the data has been updated
        video1 = models.Video.objects.get(pk=POST_data['form-0-id'])
        video2 = models.Video.objects.get(
            pk=POST_data['form-1-id'])

        for video in video1, video2:
            self.assertEquals(
                set(video.categories.values_list('pk', flat=True)),
                set([1, 2]))
            self.assertEquals(
                set(video.authors.values_list('pk', flat=True)),
                set([1, 2]))
            self.assertEquals(set(video.tags.values_list('name', flat=True)),
                                  set(['tag3', 'tag4']))

    def test_POST_bulk_delete(self):
        """
        A POST request to the bulk_edit view with a valid formset and a
        POST['action'] of 'delete' should reject the videos with the bulk
        option checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['bulk_action'] = 'delete'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        # make sure the data has been updated
        video1 = models.Video.objects.get(pk=POST_data['form-0-id'])
        self.assertEquals(video1.status, models.VIDEO_STATUS_REJECTED)

        video2 = models.Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertEquals(video2.status, models.VIDEO_STATUS_REJECTED)

    def test_POST_bulk_unapprove(self):
        """
        A POST request to the bulk_edit view with a valid formset and a
        POST['action'] of 'unapprove' should unapprove the videos with the bulk
        option checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['bulk_action'] = 'unapprove'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        # make sure the data has been updated
        video1 = models.Video.objects.get(pk=POST_data['form-0-id'])
        self.assertEquals(video1.status, models.VIDEO_STATUS_UNAPPROVED)

        video2 = models.Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertEquals(video2.status, models.VIDEO_STATUS_UNAPPROVED)

    def test_POST_bulk_feature(self):
        """
        A POST request to the bulk_edit view with a valid formset and a
        POST['action'] of 'feature' should feature the videos with the bulk
        option checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['bulk_action'] = 'feature'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        # make sure the data has been updated
        video1 = models.Video.objects.get(pk=POST_data['form-0-id'])
        self.assertTrue(video1.last_featured is not None)

        video2 = models.Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertTrue(video2.last_featured is not None)

    def test_POST_bulk_unfeature(self):
        """
        A POST request to the bulk_edit view with a valid formset and a
        POST['action'] of 'feature' should feature the videos with the bulk
        option checked.
        """
        for v in models.Video.objects.all():
            v.last_featured = datetime.datetime.now()
            v.save()

        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['bulk_action'] = 'unfeature'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        # make sure the data has been updated
        video1 = models.Video.objects.get(pk=POST_data['form-0-id'])
        self.assertTrue(video1.last_featured is None)

        video2 = models.Video.objects.get(
            pk=POST_data['form-1-id'])
        self.assertTrue(video2.last_featured is None)


# -----------------------------------------------------------------------------
# Design administration tests
# -----------------------------------------------------------------------------


class EditSiteInformationAdministrationTestCase(AdministrationBaseTestCase):

    url = reverse('localtv_admin_edit_site_information')

    def setUp(self):
        AdministrationBaseTestCase.setUp(self)
        self.POST_data = {
            'title': self.site_location.site.name,
            'tagline': self.site_location.tagline,
            'about': self.site_location.about_html,
            'sidebar': self.site_location.sidebar_html,
            'footer': self.site_location.footer_html}

    def test_GET(self):
        """
        A GET request to the edit_site_information view should render the
        'localtv/admin/edit_site_information.html' template and include 2
        forms:

        * title_form
        * sidebar_form
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/admin/edit_site_information.html')
        self.assertTrue('title_form' in response.context[0])
        self.assertTrue('sidebar_form' in response.context[0])

    def test_POST_title_failure(self):
        """
        A POST request to the edit design view with an invalid title form
        should rerender the template and include the title_form errors.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data['title'] = ''
        POST_response = c.post(self.url, )

        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEquals(POST_response.template[0].name,
                          'localtv/admin/edit_site_information.html')
        self.assertFalse(POST_response.context['title_form'].is_valid())

    def test_POST_title_long_title(self):
        """
        A POST request to the edit design view with a long (>50 character)
        title should give a form error, not a 500 error.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data.update({
                'title': 'New Title' * 10,
                'tagline': 'New Tagline',
                'about': 'New About'})
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 200)
        self.assertEquals(POST_response.template[0].name,
                          'localtv/admin/edit_site_information.html')
        self.assertFalse(POST_response.context['title_form'].is_valid())

    def test_POST_title_succeed(self):
        """
        A POST request to the edit_site_information view with a valid title
        form should save the title data and redirect back to the edit design
        view.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data.update({
                'title': 'New Title',
                'tagline': 'New Tagline',
                'about': 'New About'})
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        site_location = models.SiteLocation.objects.get(
            pk=self.site_location.pk)
        self.assertEquals(site_location.site.name, 'New Title')
        self.assertEquals(site_location.tagline, 'New Tagline')
        self.assertEquals(site_location.about_html, 'New About')


    def test_POST_sidebar_failure(self):
        """
        A POST request to the edit design view with an invalid sidebar form
        should rerender the template and include the sidebar_form errors.
        """
        # TODO(pswartz): not sure how to get the sidebar form to fail
        return

    def test_POST_sidebar_succeed(self):
        """
        A POST request to the edit_site_information view with a valid sidebar
        form should save the sidebar data and redirect back to the edit design
        view.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data.update({
                'sidebar': 'New Sidebar',
                'footer': 'New Footer'})
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        site_location = models.SiteLocation.objects.get(
            pk=self.site_location.pk)
        self.assertEquals(site_location.sidebar_html, 'New Sidebar')
        self.assertEquals(site_location.footer_html, 'New Footer')


class EditContentAdministrationTestCase(AdministrationBaseTestCase):

    url = reverse('localtv_admin_edit_content')

    def setUp(self):
        AdministrationBaseTestCase.setUp(self)
        self.POST_data = {
            'css': self.site_location.css}

    def test_GET(self):
        """
        A GET request to the edit_content view should render the
        'localtv/admin/edit_content.html' template and include 3 forms:

        * misc_form
        * comment_form.
        * email_form
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/admin/edit_content.html')
        self.assertTrue('misc_form' in response.context[0])
        self.assertTrue('comment_form' in response.context[0])
        self.assertTrue('email_form' in response.context[0])

    def test_POST_misc_failure(self):
        """
        A POST request to the edit design view with an invalid misc form should
        rerender the template and include the misc_form errors.
        """
        # TODO(pswartz): not sure how to get the misc form to fail
        return

    def test_POST_misc_succeed(self):
        """
        A POST request to the edit_content view with a valid misc form should
        save the misc data and redirect back to the edit design view.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data.update({
                'logo': file(self._data_file('logo.png')),
                'background': file(self._data_file('logo.png')),
                'display_submit_button': 'yes',
                'submission_requires_login': 'yes',
                'use_original_date': '',
                'css': 'New Css'})
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        site_location = models.SiteLocation.objects.get(
            pk=self.site_location.pk)
        self.assertEquals(site_location.css, 'New Css')
        self.assertTrue(site_location.display_submit_button)
        self.assertTrue(site_location.submission_requires_login)
        self.assertFalse(site_location.use_original_date)

        logo_data = file(self._data_file('logo.png')).read()
        site_location.logo.open()
        self.assertEquals(site_location.logo.read(), logo_data)
        site_location.background.open()
        self.assertEquals(site_location.background.read(), logo_data)

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
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        site_location = models.SiteLocation.objects.get(
            pk=self.site_location.pk)
        logo_data = file(self._data_file('logo.png')).read()
        site_location.logo.open()
        self.assertEquals(site_location.logo.read(), logo_data)
        site_location.background.open()
        self.assertEquals(site_location.background.read(), logo_data)

    def test_POST_comment_failure(self):
        """
        A POST request to the edit design view with an invalid comment form
        should rerender the template and include the comment_form errors.
        """
        # TODO(pswartz) not sure how to make the comments form fail
        return

    def test_POST_comment_succeed(self):
        """
        A POST request to the edit_content view with a valid comment form
        should save the comment data and redirect back to the edit design view.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data.update({
                'screen_all_comments': 'yes',
                'comments_email_admins': 'yes',
                'comments_required_login': 'yes'})
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        site_location = models.SiteLocation.objects.get(
            pk=self.site_location.pk)
        self.assertTrue(site_location.screen_all_comments)
        self.assertTrue(site_location.comments_email_admins)
        self.assertTrue(site_location.comments_required_login)


    def test_POST_email_failure(self):
        """
        A POST request to the edit design view with an invalid email form
        should rerender the template and include the email_form errors.
        """
        # TODO(pswartz) not sure how to make the email form fail
        return

    def test_POST_email_succeed(self):
        """
        A POST request to the edit_content view with a valid email form should
        save the email data and redirect back to the edit design view.
        """
        c = Client()
        c.login(username='admin', password='admin')
        self.POST_data.update({
                'email_on_new_video': 'yes',
                'email_review_status': 'yes'})
        POST_response = c.post(self.url, self.POST_data)

        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        site_location = models.SiteLocation.objects.get(
            pk=self.site_location.pk)
        self.assertTrue(site_location.email_on_new_video)
        self.assertTrue(site_location.email_review_status)


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
        self.assertEquals(POST_response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        site_location = models.SiteLocation.objects.get(
            pk=self.site_location.pk)
        self.assertEquals(site_location.background, '')


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
        self.assertEquals(response.template[0].name,
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
        self.assertEquals(response.template[0].name,
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
        self.assertEquals(response.template[0].name,
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
            'url': 'flatpage/',
            'content': 'flatpage content',
            }
        response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        new = FlatPage.objects.order_by('-id')[0]

        self.assertEquals(list(new.sites.all()), [self.site_location.site])

        for key, value in POST_data.items():
            if key == 'submit':
                pass
            else:
                self.assertEquals(getattr(new, key), value)

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
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        for old, new in zip(old_flatpages, FlatPage.objects.values()):
            self.assertEquals(old, new)

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
        POST_data['form-0-url'] = 'newflatpage/'
        POST_data['form-1-content'] = 'New Content'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        self.assertEquals(FlatPage.objects.count(), 5) # no one got added

        new_url = FlatPage.objects.get(url='newflatpage/')
        self.assertEquals(new_url.pk, 1)
        self.assertEquals(new_url.title, 'New Title')

        new_content = FlatPage.objects.get(url='flatpage1/')
        self.assertEquals(new_content.content, 'New Content')

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
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))

        # three flatpages got removed
        self.assertEquals(FlatPage.objects.count(), 2)

    def test_POST_bulk_delete(self):
        """
        A POST request to the flatpages view with a valid formset and a
        POST['action'] of 'delete' should reject the videos with the bulk
        option checked.
        """
        c = Client()
        c.login(username='admin', password='admin')
        response = c.get(self.url)
        formset = response.context['formset']
        POST_data = self._POST_data_from_formset(formset)

        POST_data['form-0-bulk'] = 'yes'
        POST_data['form-1-bulk'] = 'yes'
        POST_data['form-2-bulk'] = 'yes'
        POST_data['submit'] = 'Apply'
        POST_data['action'] = 'delete'

        POST_response = c.post(self.url, POST_data)
        self.assertStatusCodeEquals(POST_response, 302)
        self.assertEquals(POST_response['Location'],
                          'http://%s%s?successful' % (
                self.site_location.site.domain,
                self.url))


        # three flatpages got removed
        self.assertEquals(FlatPage.objects.count(), 2)
