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
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponseRedirect, Http404
from django.views.generic import (DetailView, CreateView, UpdateView,
                                  ListView, DeleteView)

from localtv.contrib.contests.forms import ContestAdminForm
from localtv.contrib.contests.models import (Contest,
                                             UpVotesAggregate,
                                             AllVotesAggregate)
from localtv.search.views import VIDEOS_PER_PAGE
from localtv.models import Video, SiteSettings
from localtv.utils import SortHeaders


class ContestQuerySetMixin(object):
    model = Contest

    def get_queryset(self):
        qs = super(ContestQuerySetMixin, self).get_queryset()
        return qs.filter(site=settings.SITE_ID)


class ContestDetailView(ContestQuerySetMixin, DetailView):
    context_object_name = 'contest'
    template_name = 'contests/detail.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        absolute_url = self.object.get_absolute_url()
        if request.path != absolute_url:
            return HttpResponseRedirect(absolute_url)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(ContestDetailView, self).get_context_data(**kwargs)
        base_qs = Video.objects.filter(contestvideo__contest=self.object)
        if Contest.NEW in self.object.detail_columns:
            site_settings = SiteSettings.objects.get_current()
            context['new_videos'] = base_qs.with_best_date(
                                               site_settings.use_original_date
                                            ).order_by('-best_date')

        if Contest.RANDOM in self.object.detail_columns:
            context['random_videos'] = base_qs.order_by('?')

        if Contest.TOP in self.object.detail_columns:
            if not self.object.allow_downvotes:
                top_videos = base_qs.annotate(
                    rank=UpVotesAggregate())
            else:
                # Ideally, we would not use such a naive computation of rank.
                # http://evanmiller.org/how-not-to-sort-by-average-rating.html
                top_videos = base_qs.annotate(
                    rank=AllVotesAggregate())

            context['top_videos'] = top_videos.order_by('-rank')

        return context

class ContestListingView(ListView):
    model = Video
    paginate_by = VIDEOS_PER_PAGE
    template_name = 'contests/video_listing.html'

    def get(self, request, *args, **kwargs):
        try:
            contest = Contest.objects.get(
                pk=kwargs['pk'],
                site_id=settings.SITE_ID)
        except Contest.DoesNotExist:
            raise Http404

        self.object = contest
        return super(ContestListingView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return Video.objects.filter(
            contestvideo__contest=self.object,
            site_id=settings.SITE_ID).with_best_date().order_by(
            '-best_date')


class ContestAdminListView(ContestQuerySetMixin, ListView):
    context_object_name = 'contests'
    template_name = 'localtv/admin/contests/list.html'
    paginate_by = 50

    def get_queryset(self):
        self.headers = SortHeaders(self.request, (
                                   ('Name', 'name'),
                                   ('Votes', 'vote_count'),
                                   ('Videos', 'video_count')))
        queryset = super(ContestAdminListView, self).get_queryset()
        queryset = queryset.annotate(
                                vote_count=Count('contestvideo__contestvote'),
                                video_count=Count('contestvideo'))
        return queryset.order_by(self.headers.order_by())

    def get_context_data(self, **kwargs):
        context = super(ContestAdminListView, self).get_context_data(**kwargs)
        context.update({
            'headers': self.headers
        })
        return context


class ContestAdminCreateView(ContestQuerySetMixin, CreateView):
    context_object_name = 'contest'
    template_name = 'localtv/admin/contests/edit.html'
    form_class = ContestAdminForm

    def get_success_url(self):
        return reverse('localtv_admin_contests_update',
                       kwargs={'pk': self.object.pk})


class ContestAdminUpdateView(ContestQuerySetMixin, UpdateView):
    context_object_name = 'contest'
    template_name = 'localtv/admin/contests/edit.html'
    form_class = ContestAdminForm

    def get_success_url(self):
        return reverse('localtv_admin_contests_update',
                       kwargs={'pk': self.object.pk})


class ContestAdminDeleteView(ContestQuerySetMixin, DeleteView):
    context_object_name = 'contest'
    template_name = 'localtv/admin/contests/delete.html'

    def get_success_url(self):
        return reverse('localtv_admin_contests')
