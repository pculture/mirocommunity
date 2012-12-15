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

from django.conf import settings

from tastypie import fields
from tastypie import http
from tastypie.constants import ALL_WITH_RELATIONS
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import ModelResource
from tastypie.utils.mime import build_content_type

from localtv.api.v1 import api, UserResource, VideoResource
from localtv.contrib.contests.authorization import UserAuthorization
from localtv.contrib.contests.models import Contest, ContestVote, ContestVideo


class ContestResource(ModelResource):
    videos = fields.ToManyField(VideoResource, 'videos')

    def dehydrate_votes_per_user(self, bundle):
        """
        Return `None` if `votes_per_user` is `None`.
        Return the value, otherwise.
        
        """
        if bundle.obj.votes_per_user is None:
            return None
        return bundle.obj.votes_per_user

    class Meta:
        queryset = Contest.objects.filter(site=settings.SITE_ID)
        fields = ['name', 'description', 'submissions_open', 'voting_open',
                  'display_vote_counts', 'votes_per_user', 'allow_downvotes',
                  'videos',]


class ContestVideoResource(ModelResource):
    contest = fields.ToOneField(ContestResource, 'contest', full=True)
    video = fields.ToOneField(VideoResource, 'video')
    added = fields.DateTimeField('added')
    upvotes = fields.IntegerField()
    downvotes = fields.IntegerField()

    def dehydrate_upvotes(self, bundle):
        if bundle.obj.contest.display_vote_counts:
            return bundle.obj.contestvote_set.filter(vote=ContestVote.UP).count()
        else:
            return None

    def dehydrate_downvotes(self, bundle):
        if bundle.obj.contest.display_vote_counts:
            return bundle.obj.contestvote_set.filter(vote=ContestVote.DOWN).count()
        else:
            return None

    class Meta:
        queryset = ContestVideo.objects.filter(contest__site=settings.SITE_ID)


class ContestVoteResource(ModelResource):
    contestvideo = fields.ToOneField(ContestVideoResource, 'contestvideo')
    user = fields.ToOneField(UserResource, 'user')
    vote = fields.IntegerField('vote')

    def _handle_error(self, request, error_message, response_class=http.HttpForbidden):
        data = {
            "error_message": error_message,
        }
        desired_format = self.determine_format(request)
        serialized = self.serialize(request, data, desired_format)
        response = response_class(content=serialized,
                            content_type=build_content_type(desired_format))
        raise ImmediateHttpResponse(response)

    def _verify_vote(self, contestvideo, bundle=None, request=None):

        """
        Creates a contest-vote object after ensuring:
        1. the contest has voting open,
        2. user is currently logged in,
        3. the vote they are registering is permitted.
        
        If all checks out, it returns true. Otherwise it raises an HTTP
        error immediately.

        """

        # Extract relevant data.
        contest = contestvideo.contest
        vote_value = int(bundle.data['vote']) if bundle else None

        # Verify authenticated user.
        if not request.user.is_authenticated():
            return self._handle_error(request,
                                      'User must be logged-in to vote.')

        # Verify that voting is open on the contest.
        if not contest.voting_open:
            return self._handle_error(request,
                                      'Voting is not open on %s' % contest)

        # Check vote is permissible, if there's a bundle.
        permissible_votes = (1, -1) if contest.allow_downvotes else (1,)
        if vote_value is not None and vote_value not in permissible_votes:
            return self._handle_error(request,
                                'Vote value %d not permitted.' % vote_value)

        return True

    def obj_create(self, bundle, request=None, **kwargs):
        contestvideo = ContestVideoResource().get_via_uri(bundle.data['contestvideo'])
        if self._verify_vote(contestvideo, bundle=bundle, request=request):
            # Ensure that the bundle user is the current user.
            bundle.data['user'] = UserResource().get_resource_uri(request.user)
            return super(ContestVoteResource, self).obj_create(bundle,
                                                              request=request,
                                                              **kwargs)

    def obj_update(self, bundle, request=None, **kwargs):
        contestvideo = ContestVideoResource().get_via_uri(bundle.data['contestvideo'])
        if self._verify_vote(contestvideo, bundle=bundle, request=request):
            # Ensure that the bundle user is the current user.
            bundle.data['user'] = UserResource().get_resource_uri(request.user)
            return super(ContestVoteResource, self).obj_update(bundle,
                                                              request=request,
                                                              **kwargs)

    def obj_delete(self, request=None, **kwargs):
        contestvote = ContestVote.objects.get(pk=kwargs['pk'])
        contestvideo = contestvote.contestvideo
        # Ensure that the current user owns this vote.
        if contestvote.user == request.user and \
           self._verify_vote(contestvideo, request=request):
            return super(ContestVoteResource, self).obj_delete(request,
                                                               **kwargs)

    class Meta:
        queryset = ContestVote.objects.filter(
                                 contestvideo__contest__site=settings.SITE_ID)
        authorization = UserAuthorization()
        filtering = {
            'user': ALL_WITH_RELATIONS,
            'contestvideo': ALL_WITH_RELATIONS
        }
        always_return_data = True


api.register(ContestResource())
api.register(ContestVideoResource())
api.register(ContestVoteResource())
