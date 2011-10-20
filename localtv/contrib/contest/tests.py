# Copyright 2011 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
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

#from voting.models import Vote
#
#class VotingTestCase(BaseTestCase):
#
#    fixtures = BaseTestCase.fixtures + ['videos', 'categories', 'feeds']
#
#    def setUp(self):
#        BaseTestCase.setUp(self)
#        self.video = Video.objects.get(pk=20)
#        self.category = Category.objects.get(slug='miro')
#        self.category.contest_mode = datetime.datetime.now()
#        self.category.save()
#        self.video.categories.add(self.category)
#
#    def test_voting_view_add(self):
#        """
#        A POST request to the localtv_video_vote should add a vote for that
#        video ID.
#        """
#        c = Client()
#        c.login(username='user', password='password')
#        response = c.post(reverse('localtv_video_vote',
#                                  args=(self.video.pk,
#                                        'up')))
#        self.assertStatusCodeEquals(response, 302)
#        self.assertEqual(response['Location'],
#                         'http://testserver%s' % (
#                self.video.get_absolute_url()))
#        self.assertEqual(
#            Vote.objects.count(),
#            1)
#        vote = Vote.objects.get()
#        self.assertEqual(vote.object, self.video)
#        self.assertEqual(vote.user.username, 'user')
#        self.assertEqual(vote.vote, 1)
#
#    def test_voting_view_add_twice(self):
#        """
#        Adding a vote multiple times doesn't create multiple votes.
#        """
#        c = Client()
#        c.login(username='user', password='password')
#        c.post(reverse('localtv_video_vote',
#                                  args=(self.video.pk,
#                                        'up')))
#        c.post(reverse('localtv_video_vote',
#                                  args=(self.video.pk,
#                                        'up')))
#        self.assertEqual(
#            Vote.objects.count(),
#            1)
#
#    def test_voting_view_clear(self):
#        """
#        Clearing a vote removes it from the database.
#        """
#        c = Client()
#        c.login(username='user', password='password')
#        c.post(reverse('localtv_video_vote',
#                                  args=(self.video.pk,
#                                        'up')))
#        self.assertEqual(
#            Vote.objects.count(),
#            1)
#        c.post(reverse('localtv_video_vote',
#                       args=(self.video.pk,
#                             'clear')))
#        self.assertEqual(
#            Vote.objects.count(),
#            0)
#
#    def test_voting_view_too_many_votes(self):
#        """
#        You should only be able to vote for 3 videos in a category.
#        """
#        videos = []
#        for v in Video.objects.all()[:4]:
#            v.categories.add(self.category)
#            videos.append(v)
#
#        c = Client()
#        c.login(username='user', password='password')
#
#        for video in videos:
#            c.post(reverse('localtv_video_vote',
#                           args=(video.pk,
#                                 'up')))
#
#        self.assertEqual(
#            Vote.objects.count(),
#            3)
#
#        self.assertEqual(
#            set(
#                Vote.objects.values_list(
#                    'object_id', flat=True)),
#            set([v.pk for v in videos[:3]]))
#
#    def test_voting_view_clear_with_too_many(self):
#        """
#        Even if the user has voted the maximum number of times, a clear
#        should still succeed.
#        """
#        videos = []
#        for v in Video.objects.all()[:3]:
#            v.categories.add(self.category)
#            videos.append(v)
#
#        c = Client()
#        c.login(username='user', password='password')
#
#        for video in videos:
#            c.post(reverse('localtv_video_vote',
#                           args=(video.pk,
#                                 'up')))
#
#        self.assertEqual(
#            Vote.objects.count(),
#            3)
#
#        c.post(reverse('localtv_video_vote',
#                       args=(video.pk,
#                             'clear')))
#        self.assertEqual(
#            Vote.objects.count(),
#            2)
#
#    def test_voting_view_requires_authentication(self):
#        """
#        The user must be logged in in order to vote.
#        """
#        self.assertRequiresAuthentication(reverse('localtv_video_vote',
#                                                  args=(self.video.pk,
#                                                        'up')))
#
#    def test_voting_view_voting_disabled(self):
#        """
#        If voting is not enabled for a category on the video, voting should
#        have no effect.
#        """
#        self.video.categories.clear()
#        c = Client()
#        c.login(username='user', password='password')
#        response = c.post(reverse('localtv_video_vote',
#                                  args=(self.video.pk,
#                                        'up')))
#        self.assertStatusCodeEquals(response, 302)
#        self.assertEqual(response['Location'],
#                         'http://testserver%s' % (
#                self.video.get_absolute_url()))
#        self.assertEqual(
#            Vote.objects.count(),
#            0)
#
#    def test_video_model_voting_enabled(self):
#        """
#        Video.voting_enabled() should be True if it has a voting-enabled
#        category, else False.
#        """
#        self.assertTrue(self.video.voting_enabled())
#        self.assertFalse(Video.objects.get(pk=1).voting_enabled())
#
#    def test_video_view_user_can_vote_True(self):
#        """
#        The view_video view should have a 'user_can_vote' variable which is
#        True if the user has not used all their votes.
#        """
#        c = Client()
#        c.login(username='user', password='password')
#
#        response = c.get(self.video.get_absolute_url())
#        self.assertTrue(response.context['user_can_vote'])
#
#    def test_video_view_user_can_vote_False(self):
#        """
#        If the user has used all of their votes, 'user_can_vote' should be
#        False.
#        """
#        c = Client()
#        c.login(username='user', password='password')
#
#        for video in Video.objects.all()[:3]:
#            video.categories.add(self.category)
#            c.post(reverse('localtv_video_vote',
#                           args=(video.pk,
#                                 'up')))
#
#        response = c.get(self.video.get_absolute_url())
#        self.assertFalse(response.context['user_can_vote'])
#
