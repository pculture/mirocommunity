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

from django.conf import settings
from django.db.models import Count
from django.views.generic import DetailView

from localtv.contrib.contests.models import Contest


class ContestDetailView(DetailView):
    model = Contest
    context_object_name = 'contest'
    template_name = 'contests/detail.html'

    def get_queryset(self):
        qs = super(ContestDetailView, self).get_queryset()
        return qs.filter(site=settings.SITE_ID)

    def get_context_data(self, **kwargs):
        context = super(ContestDetailView, self).get_context_data(**kwargs)
        if Contest.NEW in self.object.detail_columns:
            context['new_videos'] = self.object.videos.order_by(
                                                            '-when_submitted')
        if Contest.RANDOM in self.object.detail_columns:
            context['random_videos'] = self.object.videos.order_by('?')

        if Contest.TOP in self.object.detail_columns:
            context['top_videos'] = self.object.videos.filter(
                                              contestvote__contest=self.object
                                   ).annotate(vote_count=Count('contestvote')
                                   ).order_by('-vote_count')

        return context
