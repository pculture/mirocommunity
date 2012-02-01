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

import hashlib
import time

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from vidscraper import auto_search
from vidscraper.utils.search import intersperse_results

from localtv.exceptions import InvalidVideo
from localtv.models import Video

from vidscraper.errors import Error as VidscraperError

class LiveSearchForm(forms.Form):
    LATEST = 'latest'
    RELEVANT = 'relevant'
    ORDER_BY_CHOICES = (
        (LATEST, _('Latest')),
        (RELEVANT, _('Relevant')),
    )
    q = forms.CharField()
    order_by = forms.ChoiceField(choices=ORDER_BY_CHOICES, initial=LATEST,
                                 required=False)

    def clean_order_by(self):
        return self.cleaned_data.get('order_by') or self.LATEST

    def _get_cache_key(self):
        return 'localtv-livesearch-%s' % (
            hashlib.md5('%(q)s-%(order_by)s' % self.cleaned_data
                        ).hexdigest())

    def get_search_api_keys(self):
        return {
            'vimeo_key': getattr(settings, 'VIMEO_API_KEY', None),
            'vimeo_secret': getattr(settings, 'VIMEO_API_SECRET', None),
        }

    def get_results(self):
        cache_key = self._get_cache_key()
        results = cache.get(cache_key)
        if results is None:
            finish_by = time.time() + 20
            search_results = auto_search(self.cleaned_data['q'],
                                  order_by=self.cleaned_data['order_by'],
                                  api_keys=self.get_search_api_keys())
            results = []
            for vidscraper_video in intersperse_results(search_results, 40):
                try:
                    vidscraper_video.load()
                except VidscraperError:
                    pass
                else:
                    results.append(vidscraper_video)
                if time.time() > finish_by:
                    break # don't take forever!
            cache.set(cache_key, results)

        for vidscraper_video in results:
            video = Video.from_vidscraper_video(vidscraper_video, commit=False)
            if video.embed_code or video.file_url:
                yield video
