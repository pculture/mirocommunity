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


from datetime import datetime, timedelta

from django.contrib.sites.models import Site
from django.views.generic import ListView

from localtv.admin.livesearch.forms import LiveSearchForm
from localtv.admin.livesearch.utils import parse_querystring
from localtv.decorators import require_site_admin, referrer_redirect
from localtv.models import SavedSearch


class LiveSearchView(ListView):
    context_object_name = 'video_list'
    template_name = 'localtv/admin/livesearch_table.html'
    paginate_by = 10
    form_class = LiveSearchForm

    def get_queryset(self):
        self.form = self.form_class(request.GET)
        if self.form.is_valid():
            results = self.form.get_results()
            include_terms, exclude_terms = parse_querystring(
                                                    self.form.cleaned_data['q'])
            cache_key = "%s_exclusions" % self.form._get_cache_key(
                                                   include_terms, exclude_terms)
            cached = self.request.session.get(cache_key)
            if (cached is None or
                cached['timestamp'] < datetime.now() - timedelta(0, 0, 5)):
                # Initial session should exclude all videos that already exist
                # on the site.
                website_urls, file_urls = zip(*[(video.website_url,
                                                 video.file_url)
                                                 for video in results])
                exclusions = Video.objects.filter(website_url__in=website_urls,
                                                  file_url__in=file_urls
                                                 ).values_list('website_url',
                                                               'file_url')
                website_urls, file_urls = zip(*list(exclusions))
                cached = {
                    'timestamp': datetime.now(),
                    'website_urls': set(website_urls),
                    'file_urls': set(file_urls)
                }
                self.request.session[cache_key] = cached
            # Use the cached exclusion data to filter the videos that are
            # displayed.
            return filter(lambda x: (
                                     x.file_url not in cached['file_urls'] and
                                     x.website_url not in cached['website_urls']
                                    ), results)
        return []

    def get_context_data(self, **kwargs):
        context = super(LiveSearchView, self).get_context_data(**kwargs)
        try:
            current_video = context['page_obj'].object_list[0]
        except IndexError:
            current_video = None

        current_site = Site.objects.get_current()
        is_saved_search = False
        if self.form.is_valid():
            is_saved_search = SavedSearch.objects.filter(
                                  site=current_site,
                                  query_string=self.form.cleaned_data['q']
                              ).exists()

        context.update({
            'current_video': current_video,
            'form': self.form,
            # TODO: What are these used for? Can they be eliminated?
            'is_saved_search': None,
            'saved_searches': SavedSearch.objects.filter(
                                        site=Site.objects.get_current())
        })
        
        # Provided for backwards-compatibility reasons only.
        cleaned_data = getattr(form, 'cleaned_data', form.initial)
        context.update({
            'order_by': cleaned_data.get('order_by', 'latest'),
            'query_string': cleaned_data.get('q', '')
        })
livesearch = require_site_admin(LiveSearchView.as_view())
