# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
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

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core import mail
from django.test.client import Client

from localtv.tests import BaseTestCase
from localtv.models import Video

from localtv.playlists.models import Playlist, PlaylistItem

from notification import models as notification


class PlaylistBaseTestCase(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        self.user = User.objects.get(username='user')
        self.list = Playlist.objects.create(
            user=self.user,
            name='Test List',
            slug='test-list',
            description="This is a list for testing")

        self.video_set = [Video.objects.create(
                site=self.site_location.site,
                name='Test Video %i' % i) for i in range(5)]

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
        v = Video.objects.create(
            site=self.site_location.site,
            name='Added video')
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


class PlaylistViewTestCase(PlaylistBaseTestCase):

    fixtures = PlaylistBaseTestCase.fixtures + ['videos']

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
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
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
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain, url))

        playlist = Playlist.objects.order_by('-pk')[0]
        self.assertEqual(playlist.name, data['name'])
        self.assertEqual(playlist.slug, data['slug'])
        self.assertEqual(playlist.description, data['description'])
        self.assertEqual(playlist.status, Playlist.PRIVATE)
        self.assertEqual(playlist.video_set.count(), 0)

    def test_add_with_video_success(self):
        """
        A POST to the index view with a video (as from a video page) should
        create a new playlist with the given name, and add that vide to it.
        """
        video = Video.objects.filter(status=1)[0]
        url = reverse('localtv_playlist_index')
        data = {'name': 'New Playlist',
                'video': video.pk}
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        playlist = Playlist.objects.order_by('-pk')[0]

        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s?playlist=%i' % (
                self.site_location.site.domain,
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
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
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
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
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
        video = Video.objects.filter(status=1)[0]
        count = Playlist.objects.count()
        data = {'name': self.list.name,
                'video': video.pk}
        c = Client()
        c.login(username='user', password='password')
        response = c.post(reverse('localtv_playlist_index'), data)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
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
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_playlist_index')))
        self.assertRaises(Playlist.DoesNotExist, Playlist.objects.get,
                          pk=self.list.pk)

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
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_playlist_index')))
        self.assertRaises(Playlist.DoesNotExist, Playlist.objects.get,
                          pk=self.list.pk)

    def test_bulk_public(self):
        """
        A POST to the index with the formset data and some playlists marked
        with the bulk option and the 'public' action should mark those videos
        as waiting for moderation.
        """
        notice_type = notification.NoticeType.objects.get(
            label='admin_new_playlist')
        setting = notification.get_notification_setting(
            User.objects.get(username='admin'),
            notice_type,
            "1")
        setting.send = True
        setting.save()
        url = reverse('localtv_playlist_index')
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {
                'form-INITIAL_FORMS': 1,
                'form-TOTAL_FORMS': 1,
                'form-0-id': self.list.pk,
                'form-0-BULK': 'yes',
                'bulk_action': 'public'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain,
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
        notice_type = notification.NoticeType.objects.get(
            label='admin_new_playlist')
        setting = notification.get_notification_setting(
            User.objects.get(username='admin'),
            notice_type,
            "1")
        setting.send = True
        setting.save()
        url = reverse('localtv_playlist_index') + '?show=all'
        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url, {
                'form-INITIAL_FORMS': 1,
                'form-TOTAL_FORMS': 1,
                'form-0-id': self.list.pk,
                'form-0-BULK': 'yes',
                'bulk_action': 'public'})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain,
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
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_playlist_index')))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(playlist.status, Playlist.PRIVATE)

    def test_add_video(self):
        """
        A POST to the add_video view should add the video with the given PK to
        the playlist if the user is authorized.  If not, they should be asked
        to log in..
        """
        video = Video.objects.filter(status=1)[0]
        url = reverse('localtv_playlist_add_video', args=(video.pk,))
        self.assertRequiresAuthentication(url)

        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {'playlist': self.list.pk},
                          HTTP_REFERER=video.get_absolute_url())
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s?playlist=%i' % (
                self.site_location.site.domain,
                video.get_absolute_url(), self.list.pk))

        self.assertEqual(list(self.list.video_set.all())[-1], video)

    def test_add_video_opens_new_playlist(self):
        """
        Even if we were in a playlist before, adding a video to a playlist
        should redirect to the page with the added playlist open.
        """
        video = Video.objects.filter(status=1)[0]
        url = reverse('localtv_playlist_add_video', args=(video.pk,))
        self.assertRequiresAuthentication(url)

        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, {'playlist': self.list.pk},
                          HTTP_REFERER='%s?playlist=0' %
                          video.get_absolute_url())
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s?playlist=%i' % (
                self.site_location.site.domain,
                video.get_absolute_url(), self.list.pk))

        self.assertEqual(list(self.list.video_set.all())[-1], video)

    def test_add_video_admin(self):
        """
        Admins should be able to add videos to arbitrary playlists.
        """
        video = Video.objects.filter(status=1)[0]
        url = reverse('localtv_playlist_add_video', args=(video.pk,))

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(url, {'playlist': self.list.pk})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s?playlist=%i' % (
                self.site_location.site.domain,
                video.get_absolute_url(), self.list.pk))

        self.assertEqual(list(self.list.video_set.all())[-1], video)

    def test_view(self):
        """
        The view view should render the 'localtv/playlists/view.html' template
        and include the playlist in the context.
        """
        self.list.status = Playlist.PUBLIC
        self.list.save()

        url = reverse('localtv_playlist_view', args=(
                self.list.pk, self.list.slug))
        c = Client()
        response = c.get(url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/playlists/view.html')
        self.assertEqual(response.context['playlist'], self.list)

    def test_view_redirect(self):
        """
        If the URL isn't the full path (ID + slug), redirect to the canonical
        URL.
        """
        c = Client()
        c.login(username='user', password='password')
        for url in (reverse('localtv_playlist_view', args=(self.list.pk,)),
                    reverse('localtv_playlist_view', args=(self.list.pk,
                                                           'fake-slug'))):
            response = c.get(url)
            self.assertStatusCodeEquals(response, 301) # permanent redirect
            self.assertEqual(response['Location'], 'http://%s%s' % (
                    self.site_location.site.domain,
                    self.list.get_absolute_url()))

    def test_view_404(self):
        """
        If the playlist isn't public, the page should return a 404.
        """
        url = reverse('localtv_playlist_view', args=(
                self.list.pk, self.list.slug))
        c = Client()
        response = c.get(url, follow=True)
        self.assertStatusCodeEquals(response, 404)

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
        self.assertStatusCodeEquals(response, 200)
        self.assertEqual(response.template[0].name,
                          'localtv/playlists/edit.html')
        self.assertEqual(response.context['playlist'], self.list)
        self.assertFalse(response.context['formset'].is_bound)
        self.assertEqual(len(response.context['formset'].forms),
                          self.list.video_set.count())

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
            data['playlistitem_set-%i-playlist' % (4-index)] = self.list.pk
            data['playlistitem_set-%i-id' % (4-index)] = \
                self.list._item_for(video).pk
            data['playlistitem_set-%i-ORDER' % (4-index)] = index
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain, url))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(list(playlist.video_set.all()),
                          self.video_set)

    def test_edit_POST_ordering_down(self):
        """
        If two videos have the same number (the higher one has moved down), the
        one that changed should take precedence.
        """
         # flip the last two
        video_set = self.video_set[:3] + [self.video_set[4],
                                          self.video_set[3]]
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
        data['playlistitem_set-4-ORDER'] = 4 # 3 and 4 both have 4 as their
                                             # order
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain, url))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(list(playlist.video_set.all()),
                          video_set)

    def test_edit_POST_ordering_up(self):
        """
        If two videos have the same number (the lower one has moved up), the
        one that changed should take precedence.
        """
         # flip the last two
        video_set = self.video_set[:3] + [self.video_set[4],
                                          self.video_set[3]]
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
        data['playlistitem_set-3-ORDER'] = 5 # 3 and 4 both have 5 as their
                                             # order
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain, url))
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
            data['playlistitem_set-%i-playlist' % (4-index)] = self.list.pk
            data['playlistitem_set-%i-id' % (4-index)] = \
                self.list._item_for(video).pk
            data['playlistitem_set-%i-ORDER' % (4-index)] = 4 - index
        data['playlistitem_set-2-DELETE'] = 'yes' # delete the middle object
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain, url))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(list(playlist.video_set.all()),
                          self.video_set[:2:-1] + self.video_set[1::-1])

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
            data['playlistitem_set-%i-playlist' % (4-index)] = self.list.pk
            data['playlistitem_set-%i-id' % (4-index)] = \
                self.list._item_for(video).pk
            data['playlistitem_set-%i-ORDER' % (4-index)] = 4 - index
        data['playlistitem_set-2-BULK'] = 'yes' # delete the middle object
        data['bulk_action'] = 'delete'
        c = Client()
        c.login(username='user', password='password')
        response = c.post(url, data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain, url))
        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(list(playlist.video_set.all()),
                          self.video_set[:2:-1] + self.video_set[1::-1])

    def test_public(self):
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
        c.login(username='user', password='password')
        response = c.post(url, {})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain,
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
        c.login(username='superuser', password='superuser')
        response = c.post(url, {})
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s?show=all' % (
                self.site_location.site.domain,
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
        self.assertStatusCodeEquals(response, 302)
        self.assertEqual(response['Location'], 'http://%s%s' % (
                self.site_location.site.domain,
                reverse('localtv_playlist_index')))

        playlist = Playlist.objects.get(pk=self.list.pk)
        self.assertEqual(playlist.status, Playlist.PRIVATE)

    def test_disabled(self):
        """
        If playlists are disabled, every playlist view should return a 404.
        """
        self.site_location.playlists_enabled = False
        self.site_location.save()

        c = Client()
        for view, args in (('localtv_playlist_index', ()),
                     ('localtv_playlist_view', (1,)),
                     ('localtv_playlist_edit', (1,)),
                     ('localtv_playlist_add_video', (1,)),
                     ('localtv_playlist_public', (1,)),
                     ('localtv_playlist_private', (1,)),):
            url = reverse(view, args=args)
            response = c.get(url, follow=True)
            self.assertStatusCodeEquals(response, 404)
