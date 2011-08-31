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

from django.contrib.sites.models import Site

from haystack import forms
from localtv.models import Video
from localtv.search.query import SmartSearchQuerySet

class VideoSearchForm(forms.SearchForm):
    def __init__(self, *args, **kwargs):
        sqs = kwargs.get('searchqueryset', None)
        if sqs is None:
            kwargs['searchqueryset'] = SmartSearchQuerySet()
        super(VideoSearchForm, self).__init__(*args, **kwargs)

    def search(self):
        """
        Adjusts the searchqueryset to return only videos associated with the
        current site before performing the search.

        """
        site = Site.objects.get_current()
        self.searchqueryset = self.searchqueryset.models(
                        Video).filter(site=site.pk)
        return super(VideoSearchForm, self).search()

    def no_query_found(self):
        return self.searchqueryset.all()
