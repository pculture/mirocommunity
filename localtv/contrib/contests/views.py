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

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db.models import Sum
from django.http import Http404
from django.utils import simplejson as json
from django.utils.decorators import method_decorator
from django.views.generic import FormView, UpdateView
from voting.models import Vote

from localtv.contrib.contest.forms import VotingForm, AdminForm
from localtv.contrib.contest.models import ContestSettings
from localtv.decorators import require_site_admin
from localtv.models import CategoryVideo


class ContestVoteView(FormView):
    form_class = VotingForm


    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ContestVoteView, self).dispatch(*args, **kwargs)

    def get_success_url(self):
        return self.form.cleaned_data['video'].get_absolute_url()

    def form_valid(self, form):
        if self.request.is_ajax():
            return json.dumps({
               'success': True,
               'score': Vote.objects.get_score(form.category_video)
            })
        return super(ContestVoteView, self).form_valid()
    
    def form_invalid(self, form):
        if self.request.is_ajax():
            return json.dumps({
                'success': False,
                'errors': form.errors
            })
        return super(ContestVoteView, self).form_invalid()


class ContestAdminView(UpdateView):
    form_class = AdminForm
    template_name = 'localtv/admin/contest.html'

    @method_decorator(login_required)
    @method_decorator(require_site_admin)
    def dispatch(self, *args, **kwargs):
        return super(ContestAdminView, self).dispatch(*args, **kwargs)
    
    def get_object(self):
        return ContestSettings.objects.get_current()

    def get_context_data(self, **kwargs):
        context = super(ContestAdminView, self).get_context_data(**kwargs)
        current_categories = self.object.categories.filter(
                                    site=Site.objects.get_current())
        categories = {}
        for category in current_categories:
            videos = dict((
                (categoryvideo._get_pk_val(), categoryvideo.video)
                for categoryvideo in
                category.categoryvideo_set.select_related('video')
            ))
            ct = ContentType.objects.get_for_model(CategoryVideo)
            bulk_scores = Vote.objects.filter(
                              object_id__in=videos.keys(),
                              content_type=ct,
                          ).values_list(
                              'object_id'
                          ).annotate(
                              score=Sum('vote')
                          ).filter(
                              score__gt=0
                          ).order_by('-score')[:10]

            categories[category] = [
                {'video': videos[pk], 'score': score}
                for pk, score in bulk_scores
            ]
        context.update({'contest_categories': categories})
        return context
