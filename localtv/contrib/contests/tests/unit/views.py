# Copyright 2012 - Participatory Culture Foundation
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

import datetime

from localtv.contrib.contests.tests.base import BaseTestCase
from localtv.contrib.contests.models import Contest
from localtv.contrib.contests.views import (ContestDetailView,
                                            ContestListingView)


class ContestDetailViewUnit(BaseTestCase):
    def test_context_data__new(self):
        contest = self.create_contest(detail_columns=Contest.NEW)
        # MySQL times are only accurate to one second, so make sure the times
        # are different by a whole second.
        now = datetime.datetime.now()
        second = datetime.timedelta(seconds=1)
        video1 = self.create_video(name='video1',
                                   when_approved=now - second * 2)
        video2 = self.create_video(name='video2',
                                   when_approved=now - second)
        video3 = self.create_video(name='video3',
                                   when_approved=now)
        self.create_contestvideo(contest, video1)
        self.create_contestvideo(contest, video2)
        self.create_contestvideo(contest, video3)

        view = ContestDetailView()
        view.object = contest

        context_data = view.get_context_data(object=contest)
        self.assertEqual(list(context_data['new_videos']),
                         [video3, video2, video1])
        self.assertTrue('random_videos' not in context_data)
        self.assertTrue('top_videos' not in context_data)

    def test_context_data__random(self):
        contest = self.create_contest(detail_columns=Contest.RANDOM)
        video1 = self.create_video(name='video1')
        video2 = self.create_video(name='video2')
        video3 = self.create_video(name='video3')
        self.create_contestvideo(contest, video1)
        self.create_contestvideo(contest, video2)
        self.create_contestvideo(contest, video3)

        view = ContestDetailView()
        view.object = contest

        context_data = view.get_context_data(object=contest)
        self.assertTrue('random_videos' in context_data)
        self.assertTrue('new_videos' not in context_data)
        self.assertTrue('top_videos' not in context_data)

        # Try to test whether the videos are randomly arranged.
        random = list(context_data['random_videos'])
        contexts = [view.get_context_data(object=contest)
                    for i in xrange(10)]
        self.assertTrue(any([random != list(c['random_videos'])
                             for c in contexts]))
        
    def test_context_data__top(self):
        contest = self.create_contest(detail_columns=Contest.TOP,
                                      allow_downvotes=False)
        video1 = self.create_video(name='video1')
        video2 = self.create_video(name='video2')
        video3 = self.create_video(name='video3')
        cv1 = self.create_contestvideo(contest, video1, upvotes=5)
        self.create_contestvideo(contest, video2, upvotes=10)
        self.create_contestvideo(contest, video3, upvotes=3)

        view = ContestDetailView()
        view.object = contest

        context_data = view.get_context_data(object=contest)
        self.assertEqual(list(context_data['top_videos']),
                         [video2, video1, video3])
        self.assertTrue('random_videos' not in context_data)
        self.assertTrue('new_videos' not in context_data)

        # Downvotes should be ignored if they're disallowed.  By adding 6 down
        # votes to the video with 5 votes, if the down votes are counted at all
        # that video will be in the wrong place.
        self.create_votes(cv1, 6, are_up=False)
        context_data = view.get_context_data(object=contest)
        self.assertEqual(list(context_data['top_videos']),
                         [video2, video1, video3])

        # ... and taken into account otherwise.
        contest.allow_downvotes = True
        context_data = view.get_context_data(object=contest)
        self.assertEqual(list(context_data['top_videos']),
                         [video2, video3, video1])


class ContestListingViewUnit(BaseTestCase):

    def test_get_queryset(self):
        contest = self.create_contest()
        now = datetime.datetime.now()
        second = datetime.timedelta(seconds=1)
        video1 = self.create_video(name='video1',
                                           when_approved=now - second * 2)
        video2 = self.create_video(name='video2',
                                           when_approved=now - second)
        video3 = self.create_video(name='video3',
                                           when_approved=now)
        self.create_contestvideo(contest, video1)
        self.create_contestvideo(contest, video2)
        self.create_contestvideo(contest, video3)

        view = ContestListingView()
        view.object = contest

        self.assertEqual(list(view.get_queryset()),
                         [video3, video2, video1])

    def test_get(self):
        contest = self.create_contest()
        view = ContestListingView()
        self.assertTrue(view.dispatch(self.factory.get('/'),
                                      pk=contest.pk,
                                      slug=contest.slug))
        self.assertEqual(view.object, contest)
