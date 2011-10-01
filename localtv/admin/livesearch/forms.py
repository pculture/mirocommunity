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

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from vidscraper import auto_search
from vidscraper.utils.search import intersperse_results

from localtv.admin.livesearch.utils import parse_querystring, terms_for_cache
from localtv.models import Video


class LiveSearchForm(forms.Form):
    LATEST = 'latest'
    RELEVANT = 'relevant'
    ORDER_BY_CHOICES = (
        (LATEST, _('Latest')),
        (RELEVANT, _('Relevant')),
    )
    q = forms.CharField()
    order_by = forms.ChoiceField(choices=ORDER_BY_CHOICES, default=LATEST)

    def _get_cache_key(self, include_terms, exclude_terms):
        return 'localtv-livesearch-%s' % terms_for_cache(include_terms,
                                                         exclude_terms)

    def get_search_kwargs(self):
        return {
            'vimeo_api_key': getattr(settings, 'VIMEO_API_KEY', None),
            'vimeo_api_secret': getattr(settings, 'VIMEO_API_SECRET', None),
        }

    def get_results(self):
        include_terms, exclude_terms = parse_querystring(self.cleaned_data['q'])
        cache_key = self._get_cache_key(include_terms, exclude_terms)
        results = cache.get(cache_key)
        if results is None:
            results = auto_search(include_terms, exclude_terms,
                                  self.cleaned_data['order_by'],
                                  **self.get_search_kwargs())

            results = [Video.from_scraped_video(scraped) for scraped in
                       intersperse_results(results, 40)]
            cache.set(cache_key, results)

        return results
