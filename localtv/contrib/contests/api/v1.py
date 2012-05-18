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
from tastypie.constants import ALL_WITH_RELATIONS
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpUnauthorized
from tastypie.resources import ModelResource

from localtv.api.v1 import api, UserResource, VideoResource
from localtv.contrib.contests.authorization import UserAuthorization
from localtv.contrib.contests.models import Contest, ContestVote, ContestVideo

class ContestResource(ModelResource):
    votes = fields.ToManyField(
                'localtv.contrib.contests.api.v1.ContestVoteResource',
                'votes')
    videos = fields.ToManyField(VideoResource, 'videos')

    class Meta:
        queryset = Contest.objects.filter(site=settings.SITE_ID)


class ContestVideoResource(ModelResource):
    contest = fields.ToOneField(ContestResource, 'contest')
    video = fields.ToOneField(VideoResource, 'video')
    added = fields.DateTimeField('added')

    class Meta:
        queryset = ContestVideo.objects.filter(contest__site=settings.SITE_ID)


class ContestVoteResource(ModelResource):
    contestvideo = fields.ToOneField(ContestVideoResource, 'contestvideo')
    user = fields.ToOneField(UserResource, 'user')
    vote = fields.IntegerField('vote')

    def obj_create(self, bundle, request=None, **kwargs):
        if hasattr(request, 'user') and request.user.is_authenticated():
            kwargs['user'] = request.user
        else:
            raise ImmediateHttpResponse(response=HttpUnauthorized())
        return super(ContestVoteResource, self).obj_create(bundle,
                                                           request=request,
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
