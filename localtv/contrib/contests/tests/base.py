from hashlib import sha1

from django.contrib.auth.models import User

from localtv.contrib.contests.models import Contest, ContestVote, ContestVideo
from localtv.tests.base import BaseTestCase as LocaltvBaseTestCase


class BaseTestCase(LocaltvBaseTestCase):
    def create_contest(self, name='Contest', site_id=1, **kwargs):
        """
        Creates a contest. Provides defaults for the required values.

        """
        return Contest.objects.create(name=name, site_id=site_id, **kwargs)

    def create_vote(self, contestvideo, user, is_up=True):
        """
        Creates a vote by the given ``user`` for the given ``contestvideo``;
        by default, creates an upvote.

        """
        vote = ContestVote.UP if is_up else ContestVote.DOWN
        return ContestVote.objects.create(contestvideo=contestvideo,
                                          user=user, vote=vote)

    def create_contestvideo(self, contest, video, upvotes=0, downvotes=0):
        """
        Creates a connection between the given video and contest, with the
        given number of votes.

        """
        contestvideo = ContestVideo.objects.create(contest=contest, video=video)
        self.create_votes(contestvideo, upvotes, are_up=True)
        self.create_votes(contestvideo, downvotes, are_up=False)
        return contestvideo

    def create_votes(self, contestvideo, votes=0, are_up=True):
        """
        Creates a number of votes for the given contestvideo. Users are
        created with hashed usernames to supply the votes.

        """
        for i in xrange(votes):
            username = sha1(unicode(contestvideo.pk) + unicode(i) +
                            unicode(are_up)).hexdigest()[::2]
            user = self.create_user(username=username)
            self.create_vote(contestvideo, user, are_up)
