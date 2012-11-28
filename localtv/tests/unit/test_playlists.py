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


from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core import mail
from django.test.client import Client
from django.http import Http404

from localtv.tests import BaseTestCase
from localtv.models import SiteSettings

from localtv.playlists.models import Playlist, PlaylistItem
from localtv.playlists import views

from notification import models as notification

class PlaylistBaseTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.user = self.create_user(username='user', password='password')
        self.list = Playlist.objects.create(
            site_id=settings.SITE_ID,
            user=self.user,
            name='Test List',
            slug='test-list',
            description="This is a list for testing")

        self.video_set = [self.create_video() for i in range(3)]

        for index, video in enumerate(self.video_set[::-1]): # reverse order
            PlaylistItem.objects.create(
                playlist=self.list,
                video=video,
                _order=index)


class PlaylistModelTestCase(PlaylistBaseTestCase):
    def test_ordering(self):
        """
        Playlist.videos.all() should return the videos in the order determined
        by the ordering field in the PlaylistItem model.
        """
        self.assertEqual(
            list(self.list.video_set.all()),
            self.video_set[::-1])

    def test_order_videos(self):
        """
        Playlist.order_videos() should reorder the videos.
        """
        self.list.order_videos(self.video_set) # regular order
        self.assertEqual(
            list(self.list.video_set.all()),
            self.video_set)


    def test_add_video(self):
        """
        Playlist.add_video() should add a video to the end of the playlist.
        """
        v = self.create_video()
        self.list.add_video(v)
        self.assertEqual(list(self.list.video_set.all())[-1],
                          v)

    def test_no_duplicates(self):
        """
        Playlist.add_video() should not allow a video to be added to a playlist
        twice.
        """
        self.assertRaises(Exception,
                          self.list.add_video, self.video_set[0])

    def test_next_video(self):
        """
        Playlist.next_video(video) should return the next video in the
        playlist, or None if there is no next video.
        """
        nexts = [None] + self.video_set[:-1] # first video in video_set is
                                              # the end of the playlist
        self.assertEqual([self.list.next_video(video)
                           for video in self.video_set],
                          nexts)

    def test_previous_video(self):
        """
        Playlist.previous_video(video) should return the previous video in the
        playlist, or None if there is no previous video.
        """
        prevs = self.video_set[1:] + [None] # all but the first video, plus
                                             # None
        self.assertEqual([self.list.previous_video(video)
                           for video in self.video_set],
                          prevs)


class PlaylistViewClassTestCase(PlaylistBaseTestCase):
    def setUp(self):
        PlaylistBaseTestCase.setUp(self)
        self.request = self.factory.get(self.list.get_absolute_url(),
                                        user=self.user)
        self.view = views.PlaylistView()
        self.view.dispatch(self.request, self.list.pk)

    def test_get_paginate_by(self):
        self.assertEqual(self.view.get_paginate_by(self.request), 15)
        self.view.dispatch(self.request, self.list.pk, count=30)
        self.assertEqual(self.view.get_paginate_by(self.request), 30)

    def test_get_queryset(self):
        self.assertEqual(list(self.view.get_queryset()),
                         list(self.list.video_set))

    def test_get_context_data(self):
        context = self.view.get_context_data(object_list=self.list.video_set)
        self.assertEqual(context['playlist'], self.list)
        self.assertEqual(context['video_url_extra'],
                         '?playlist=%i' % self.list.pk)

    def test_get_template_names(self):
        """
        PlaylistView checks both the old path 'localtv/playlists/view.html' as
        well as the new 'localtv/video_listing_playlist.html'.
        """
        self.assertEqual(self.view.get_template_names(),
                         ('localtv/playlists/view.html',
                          'localtv/video_listing_playlist.html'))

    def test_404_if_private(self):
        """
        If the playlist is private, and the user isn't an admin or the user who
        owns the playlist, the view should raise Http404.
        """
        # owner
        request = self.factory.get(self.list.get_absolute_url(),
                                   user=self.user)
        self.assertEqual(self.view.dispatch(request, self.list.pk).status_code,
                         200)

        # anonymous
        request = self.factory.get(self.list.get_absolute_url())
        self.assertRaises(Http404, self.view.dispatch, request, self.list.pk)

        # another user
        other_user = self.create_user("other_user")
        request = self.factory.get(self.list.get_absolute_url(),
                                   user=other_user)
        self.assertRaises(Http404, self.view.dispatch, request, self.list.pk)

        # admin
        admin = self.create_user("admin", is_superuser=True)
        request = self.factory.get(self.list.get_absolute_url(),
                                   user=admin)
        self.assertEqual(self.view.dispatch(request, self.list.pk).status_code,
                         200)

    def test_redirect(self):
        """
        If the user goes to the wrong URL for a playlist, they should be
        non-permanently redirected to the correct location.
        """
        request = self.factory.get('/',
                                   user=self.user)
        response = self.view.dispatch(request, self.list.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], self.list.get_absolute_url())


class PlaylistViewTestCase(PlaylistBaseTestCase):
    def test_index(self):
        """
        The index view should show the list of playlists for the user.  If the
        user isn't logged in, they should be redirected to the login page
        instead.
        """
        url = reverse('localtv_playlist_index')
        self.assertRequiresAuthentication(url)

        c = Client()
        c.login(username='user', password='password')
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/playlists/index.html')
        self.assertEqual([form.instance for form in
                           response.context['formset'].forms], [self.list])
        self.assertFalse(response.context['form'].is_bound)

    def test_add_success(self):
        """
        A POST to the index view with all the form data should create a new
        playlist.
        """
        url = reverse('localtv_playlist_index')
        data = {'name': 'New Playlist',
                'slug': 'new-playlist',
                'description': "A brand new playlist!"}
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver', url))

        playlist = Playlist.objects.order_by('-pk')[0]
        self.assertEqual(playlist.name, data['name'])
        self.assertEqual(playlist.slug, data['slug'])
        self.assertEqual(playlist.description, data['description'])
        self.assertEqual(playlist.status, Playlist.PRIVATE)
        self.assertEqual(playlist.video_set.count(), 0)

    def test_add_with_video_success(self):
        """
        A POST to the index view with a video (as from a video page) should
        create a new playlist with the given name, and add that video to it.
        """
        video = self.create_video()
        url = reverse('localtv_playlist_index')
        data = {'name': 'New Playlist',
                'video': video.pk}
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        playlist = Playlist.objects.order_by('-pk')[0]

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s?playlist=%i' % (
                'testserver',
                video.get_absolute_url(), playlist.pk))

        self.assertEqual(playlist.name, data['name'])
        self.assertEqual(playlist.slug, 'new-playlist')
        self.assertEqual(playlist.description, '')
        self.assertEqual(playlist.status, Playlist.PRIVATE)
        self.assertEqual(list(playlist.video_set.all()), [video])

    def test_add_failure(self):
        """
        A POST to the index without all the appropriate data should reload the
        page with the form having some data.
        """
        count = Playlist.objects.count()
        c = Client()
        c.login(username='user', password='password')
        response = c.post(reverse('localtv_playlist_index'), {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/playlists/index.html')
        self.assertEqual([form.instance for form in
                           response.context['formset'].forms], [self.list])
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())
        self.assertEqual(Playlist.objects.count(), count)  # no new Playlist

    def test_add_failure_duplicate(self):
        """
        If a playlist is added that already exists, the form should fail.
        """
        count = Playlist.objects.count()
        c = Client()
        c.login(username='user', password='password')
        response = c.post(reverse('localtv_playlist_index'), {
                'name': self.list.name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/playlists/index.html')
        self.assertEqual([form.instance for form in
                           response.context['formset'].forms], [self.list])
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())
        self.assertEqual(Playlist.objects.count(), count)  # no new Playlist

    def test_add_with_video_failure(self):
        """
        A POST to the index with a video, but an error (say a duplicate name),
        should result in an error.
        """
        video = self.create_video()
        count = Playlist.objects.count()
        data = {'name': self.list.name,
                'video': video.pk}
        c = Client()
        c.login(username='user', password='password')
        response = c.post(reverse('localtv_playlist_index'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/playlists/index.html')
        self.assertEqual([form.instance for form in
                           response.context['formset'].forms], [self.list])
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())
        self.assertEqual(Playlist.objects.count(), count)  # no new Playlist

    def test_delete(self):
        """
        A POST to the index with the formset data and some playlists marked for
        deletion, they should be deleted.
        """
        url = reverse('localtv_playlist_index')
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {
                'form-INITIAL_FORMS': 1,
                'form-TOTAL_FORMS': 1,
                'form-0-id': self.list.pk,
                'form-0-DELETE': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver',
                reverse('localtv_playlist_index')))
        self.assertRaises(Playlist.DoesNotExist, Playlist.objects.get,
                          pk=self.list.pk)

    def test_add_video(self):
        """
        A POST to the add_video view should add the video with the given PK to
        the playlist if the user is authorized.  If not, they should be asked
        to log in..
        """
        video = self.create_video()
        url = reverse('localtv_playlist_add_video', args=(video.pk,))
        self.assertRequiresAuthentication(url)

        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {'playlist': self.list.pk},
                          HTTP_REFERER=video.get_absolute_url())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s?playlist=%i' % (
                'testserver',
                video.get_absolute_url(), self.list.pk))

        self.assertEqual(list(self.list.video_set.all())[-1], video)

    def test_add_video_opens_new_playlist(self):
        """
        Even if we were in a playlist before, adding a video to a playlist
        should redirect to the page with the added playlist open.
        """
        video = self.create_video()
        url = reverse('localtv_playlist_add_video', args=(video.pk,))
        self.assertRequiresAuthentication(url)

        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {'playlist': self.list.pk},
                          HTTP_REFERER='%s?playlist=0' %
                          video.get_absolute_url())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s?playlist=%i' % (
                'testserver',
                video.get_absolute_url(), self.list.pk))

        self.assertEqual(list(self.list.video_set.all())[-1], video)

    def test_add_video_admin(self):
        """
        Admins should be able to add videos to arbitrary playlists.
        """
        self.create_user(username='admin', is_superuser=True,
                         password='admin')

        video = self.create_video()
        url = reverse('localtv_playlist_add_video', args=(video.pk,))

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url, {'playlist': self.list.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s?playlist=%i' % (
                'testserver',
                video.get_absolute_url(), self.list.pk))

        self.assertEqual(list(self.list.video_set.all())[-1], video)

    def test_edit(self):
        """
        The edit view should render the 'localtv/playlists/edit.html' view, and
        include a formset of the items so that they can be reordered.
        Unauthorized users should be redirected to the login page.
        """
        url = reverse('localtv_playlist_edit', args=(self.list.pk,))
        self.assertRequiresAuthentication(url)
        c = Client()
        c.login(username='user', password='password')
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name,
                          'localtv/playlists/edit.html')
        self.assertEqual(response.context['playlist'], self.list)
        self.assertFalse(response.context['formset'].is_bound)
        self.assertEqual(len(response.context['formset'].forms),
                          self.list.video_set.count())


    def test_bulk_delete(self):
        """
        A POST to the index with the formset data and some playlists marked
        with the bulk option and the 'delete action should delete those
        playlists.
        """
        url = reverse('localtv_playlist_index')
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {
                'form-INITIAL_FORMS': 1,
                'form-TOTAL_FORMS': 1,
                'form-0-id': self.list.pk,
                'form-0-BULK': 'yes',
                'bulk_action': 'delete'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver',
                reverse('localtv_playlist_index')))
        self.assertRaises(Playlist.DoesNotExist, Playlist.objects.get,
                          pk=self.list.pk)

    def test_edit_POST_success(self):
        """
        If we make a successful POST request to the edit view, it should update
        the ordering of the playlist.
        """
        url = reverse('localtv_playlist_edit', args=(self.list.pk,))
        data = {
            'playlistitem_set-INITIAL_FORMS': len(self.video_set),
            'playlistitem_set-TOTAL_FORMS': len(self.video_set),
            }
        for index, video in enumerate(self.video_set):
            data['playlistitem_set-%i-playlist' % (2-index)] = self.list.pk
            data['playlistitem_set-%i-id' % (2-index)] = \
                self.list._item_for(video).pk
            data['playlistitem_set-%i-ORDER' % (2-index)] = index
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver', url))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(list(playlist.video_set.all()),
                          self.video_set)

    def test_edit_POST_ordering_down(self):
        """
        If two videos have the same number (the higher one has moved down), the
        one that changed should take precedence.
        """
         # flip the last two
        video_set = self.video_set[:1] + [self.video_set[2],
                                          self.video_set[1]]
        url = reverse('localtv_playlist_edit', args=(self.list.pk,))
        data = {
            'playlistitem_set-INITIAL_FORMS': len(self.video_set),
            'playlistitem_set-TOTAL_FORMS': len(self.video_set),
            }
        for index, video in enumerate(self.video_set):
            data['playlistitem_set-%i-playlist' % index] = self.list.pk
            data['playlistitem_set-%i-id' % index] = \
                self.list._item_for(video).pk
            data['playlistitem_set-%i-ORDER' % index] = index + 1  # 1-indexed
        data['playlistitem_set-2-ORDER'] = 2 # 3 and 4 both have 4 as their
                                             # order
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver', url))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(list(playlist.video_set.all()),
                          video_set)

    def test_edit_POST_ordering_up(self):
        """
        If two videos have the same number (the lower one has moved up), the
        one that changed should take precedence.
        """
         # flip the last two
        video_set = self.video_set[:1] + [self.video_set[2],
                                          self.video_set[1]]
        url = reverse('localtv_playlist_edit', args=(self.list.pk,))
        data = {
            'playlistitem_set-INITIAL_FORMS': len(self.video_set),
            'playlistitem_set-TOTAL_FORMS': len(self.video_set),
            }
        for index, video in enumerate(self.video_set):
            data['playlistitem_set-%i-playlist' % index] = self.list.pk
            data['playlistitem_set-%i-id' % index] = \
                self.list._item_for(video).pk
            data['playlistitem_set-%i-ORDER' % index] = index + 1  # 1-indexed
        data['playlistitem_set-1-ORDER'] = 3 # 2 and 3 both have 2 as their
                                             # order
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver', url))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(list(playlist.video_set.all()),
                          video_set)

    def test_edit_POST_delete(self):
        """
        Using the delete option on the formset should remove the video from the
        playlist.
        """
        url = reverse('localtv_playlist_edit', args=(self.list.pk,))
        data = {
            'playlistitem_set-INITIAL_FORMS': len(self.video_set),
            'playlistitem_set-TOTAL_FORMS': len(self.video_set),
            }
        for index, video in enumerate(self.video_set):
            data['playlistitem_set-%i-playlist' % (2-index)] = self.list.pk
            data['playlistitem_set-%i-id' % (2-index)] = \
                self.list._item_for(video).pk
            data['playlistitem_set-%i-ORDER' % (2-index)] = 2 - index
        data['playlistitem_set-1-DELETE'] = 'yes' # delete the middle object
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver', url))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(list(playlist.video_set.all()),
                         [self.video_set[2], self.video_set[0]])

    def test_edit_POST_bulk_delete(self):
        """
        Using the bulk edit field and the bulk 'delete' option should remove
        the given videos.
        """
        url = reverse('localtv_playlist_edit', args=(self.list.pk,))
        data = {
            'playlistitem_set-INITIAL_FORMS': len(self.video_set),
            'playlistitem_set-TOTAL_FORMS': len(self.video_set),
            }
        for index, video in enumerate(self.video_set):
            data['playlistitem_set-%i-playlist' % (2-index)] = self.list.pk
            data['playlistitem_set-%i-id' % (2-index)] = \
                self.list._item_for(video).pk
            data['playlistitem_set-%i-ORDER' % (2-index)] = 2 - index
        data['playlistitem_set-1-BULK'] = 'yes' # delete the middle object
        data['bulk_action'] = 'delete'
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver', url))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(list(playlist.video_set.all()),
                          [self.video_set[2], self.video_set[0]])


class PlaylistModerationTestCase(BaseTestCase):
    def setUp(self):
        admin = self.create_user(username='admin', email='admin@example.com',
                                 is_superuser=True, password='admin')

        self.user = self.create_user(username='user', password='password')

        notice_type = notification.NoticeType.objects.get(
            label='admin_new_playlist')
        setting = notification.get_notification_setting(
            User.objects.get(username='admin'),
            notice_type,
            "1")
        setting.send = True
        setting.save()

        self.list = Playlist.objects.create(
            site_id=settings.SITE_ID,
            user=self.user,
            name='Test List',
            slug='test-list',
            description="This is a list for testing")

    def test_public(self):
        """
        The localtv_playlist_public view should set the playlist's status to
        Playlist.WAITING_FOR_MODERATION and send a notification e-mail.
        """
        url = reverse('localtv_playlist_public', args=(self.list.pk,))
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver',
                reverse('localtv_playlist_index')))

        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(playlist.status,
                          Playlist.WAITING_FOR_MODERATION)
        self.assertEqual(len(mail.outbox), 1)

    def test_public_admin(self):
        """
        The localtv_playlist_public view should set the playlist's status to
        Playlist.WAITING_FOR_MODERATION and send a notification e-mail.
        """
        notice_type = notification.NoticeType.objects.get(
            label='admin_new_playlist')
        setting = notification.get_notification_setting(
            User.objects.get(username='admin'),
            notice_type,
            "1")
        setting.send = True
        setting.save()

        url = reverse('localtv_playlist_public', args=(self.list.pk,))
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url, {})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s?show=all' % (
                'testserver',
                reverse('localtv_playlist_index')))

        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(playlist.status, Playlist.PUBLIC)
        self.assertEqual(len(mail.outbox), 0)

    def test_private(self):
        """
        The localtv_playlist_private view should set the playlist's status to
        Playlist.PRIVATE.
        """
        self.list.status = Playlist.PUBLIC
        self.list.save()

        url = reverse('localtv_playlist_private', args=(self.list.pk,))
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver',
                reverse('localtv_playlist_index')))

        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(playlist.status, Playlist.PRIVATE)

    def test_bulk_public(self):
        """
        A POST to the index with the formset data and some playlists marked
        with the bulk option and the 'public' action should mark those videos
        as waiting for moderation.
        """
        url = reverse('localtv_playlist_index')
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {
                'form-INITIAL_FORMS': 1,
                'form-TOTAL_FORMS': 1,
                'form-0-id': self.list.pk,
                'form-0-BULK': 'yes',
                'bulk_action': 'public'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver',
                reverse('localtv_playlist_index')))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(playlist.status, Playlist.WAITING_FOR_MODERATION)
        self.assertEqual(len(mail.outbox), 1)

    def test_bulk_public_admin(self):
        """
        A POST to the index with the formset data and some playlists marked
        with the bulk option and the 'public' action should mark those videos
        as public if the user is an admin.
        """
        url = reverse('localtv_playlist_index') + '?show=all'
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url, {
                'form-INITIAL_FORMS': 1,
                'form-TOTAL_FORMS': 1,
                'form-0-id': self.list.pk,
                'form-0-BULK': 'yes',
                'bulk_action': 'public'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver',
                reverse('localtv_playlist_index')))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(playlist.status, Playlist.PUBLIC)
        self.assertEqual(len(mail.outbox), 0)

    def test_bulk_private(self):
        """
        A POST to the index with the formset data and some playlists marked
        with the bulk option and the 'private' action should mark those videos
        as private.
        """
        self.list.status = Playlist.PUBLIC
        self.list.save()

        url = reverse('localtv_playlist_index')
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {
                'form-INITIAL_FORMS': 1,
                'form-TOTAL_FORMS': 1,
                'form-0-id': self.list.pk,
                'form-0-BULK': 'yes',
                'bulk_action': 'private'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                'testserver',
                reverse('localtv_playlist_index')))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(playlist.status, Playlist.PRIVATE)


class PlaylistsDisabledTestCase(BaseTestCase):
    def test_disabled(self):
        """
        If playlists are disabled, every playlist view should return a 404.
        """
        site_settings = SiteSettings.objects.get_current()
        site_settings.playlists_enabled = False
        site_settings.save()

        c = Client()
        for view, args in (('localtv_playlist_index', ()),
                     ('localtv_playlist_view', (1,)),
                     ('localtv_playlist_edit', (1,)),
                     ('localtv_playlist_add_video', (1,)),
                     ('localtv_playlist_public', (1,)),
                     ('localtv_playlist_private', (1,)),):
            url = reverse(view, args=args)
            response = c.get(url, follow=True)
            self.assertEqual(response.status_code, 404)
