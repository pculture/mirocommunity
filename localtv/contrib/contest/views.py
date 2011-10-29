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
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import simplejson as json
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from voting.models import Vote

from localtv.contrib.contest.forms import VotingForm
from localtv.contrib.contest.models import ContestSettings
from localtv.models import CategoryVideo


class ContestVoteView(FormView):
    form_class = VotingForm

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ContestVoteView, self).dispatch(*args, **kwargs)

    def get_success_url(self):
        return self.form.cleaned_data['video'].get_absolute_url()

    def get_form_kwargs(self):
        kwargs = super(ContestVoteView, self).get_form_kwargs()
        if request.method == 'GET':
            kwargs.update({'data': request.GET or None})
        return kwargs

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



### OLD CODE WARNING! ;-) ###


# Video detail view hack.
# Adds whether a user can vote on the "current category" to the context
#    import voting
#    user_can_vote = True
#    if request.user.is_authenticated():
#        max_votes = video.categories.filter(
#            contest_mode__isnull=False).count() * MAX_VOTES_PER_CATEGORY
#        votes = voting.models.Vote.objects.filter(
#            content_type=ContentType.objects.get_for_model(Video),
#            user=request.user).count()
#        if votes >= max_votes:
#            user_can_vote = False
#    context['user_can_vote'] = user_can_vote
#    if user_can_vote:
#        if 'category' in context and context['category'].contest_mode:
#            context['contest_category'] = context['category']
#        else:
#            context['contest_category'] = video.categories.filter(
#                contest_mode__isnull=False)[0]


# Video vote hack. Need to override the normal video vote view to make sure
# that the user hasn't voted for too many different videos. Note: AFAICT this
# just checks that the total number of votes is less than the total number of
# possible votes, rather than checking that the total number of votes for videos
# for a certain category is less than the max number of votes for a given
# category. Of course, the only way to actually track that would be to track
# votes on a (video, category) combination - i.e. on the through model.
def video_vote(request, object_id, direction, **kwargs):
    if request.user.is_authenticated() and direction != 'clear':
        video = get_object_or_404(Video, pk=object_id)
        max_votes = video.categories.filter(
            contest_mode__isnull=False).count() * MAX_VOTES_PER_CATEGORY
        votes = voting.models.Vote.objects.filter(
            content_type=ContentType.objects.get_for_model(Video),
            user=request.user).count()
        if votes >= max_votes:
            return HttpResponseRedirect(video.get_absolute_url())
    return voting.views.vote_on_object(request, Video,
                                       direction=direction,
                                       object_id=object_id,
                                       **kwargs)


# Rather than have a categoryvideosearchview, the search_index should be
# overridden (perhaps) to provide the video/category through model as a
# select_related. Alternatively, add a template tag which, given a category
# instance, returns whether a given user can vote in that category. Has the
# advantage of being reusable on the video detail page.
class CategoryVideoSearchView(VideoSearchView):
    """
    Adds support for voting on categories. Essentially, all this means is that
    a ``user_can_vote`` variable is added to the context.

    """
    def get_context_data(self, **kwargs):
        context = VideoSearchView.get_context_data(self, **kwargs)
        category = context['category']

        user_can_vote = False
        if (localtv.settings.voting_enabled() and 
                    category.contest_mode and
                    self.request.user.is_authenticated()):
            # TODO: Benchmark this against a version where the pk queryset is
            # evaluated here instead of becoming a subquery.
            pks = category.approved_set.filter(
                site=Site.objects.get_current()).values_list('id', flat=True)
            user_can_vote = True
            votes = Vote.objects.filter(
                    content_type=ContentType.objects.get_for_model(Video),
                    object_id__in=pks,
                    user=self.request.user).count()
            if votes >= MAX_VOTES_PER_CATEGORY:
                user_can_vote = False
        context['user_can_vote'] = user_can_vote
        return context



# Heck, who knows how we'll end up hooking into the admin. This is how the votes
# used to be displayed.
@require_site_admin
def votes(request, slug):
    if not localtv.settings.voting_enabled():
        raise Http404
    
    category = get_object_or_404(Category, slug=slug)

    def score_key((k, v)):
        return v['score']

    def sorted_scores():
        videos = category.approved_set.only('id')
        import voting
        scores = voting.models.Vote.objects.get_scores_in_bulk(videos)

        for video_pk, score_dict in sorted(scores.items(),
                                           key=score_key,
                                           reverse=True):
            yield Video.objects.get(pk=video_pk), score_dict

    return render_to_response('localtv/admin/category_votes.html',
                              {'category': category,
                               'sorted_scores': sorted_scores()
                               },
                              context_instance=RequestContext(request))
