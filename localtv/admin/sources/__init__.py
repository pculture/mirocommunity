# Copyright 2010 - Participatory Culture Foundation
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

from django.conf.urls.defaults import url, patterns, include
from django.contrib.sites.models import Site
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DeleteView

from localtv.admin.base import MiroCommunityAdminSection, registry, CRUDSection
from localtv.admin.sources.forms import (SearchUpdateForm, FeedUpdateForm,
                                         FeedCreateForm, SearchCreateForm)
from localtv.admin.sources.views import SourceCreateView
from localtv.decorators import require_site_admin
from localtv.models import Feed, SavedSearch
from localtv.tasks import feed_update, search_update


class FeedSection(CRUDSection):
    create_form_class = FeedCreateForm
    update_form_class = FeedUpdateForm

    create_view_class = SourceCreateView

    template_prefixes = (
        'localtv/admin/sources/feeds/',
        'localtv/admin/sources/',
        'localtv/admin/',
    )

    def get_queryset(self):
        current_site = Site.objects.get_current()
        return Feed.objects.filter(site=current_site)

    def get_list_view_kwargs(self):
        kwargs = super(FeedSection, self).get_list_view_kwargs()
        kwargs['queryset'] = kwargs['queryset'].annotate(
                                                    video_count=Count('video'))
        return kwargs

    def get_create_view_kwargs(self):
        kwargs = super(FeedSection, self).get_create_view_kwargs()
        kwargs.update({
            'import_task': feed_update
        })
        return kwargs


class SearchSection(CRUDSection):
    create_form_class = SearchCreateForm
    update_form_class = SearchUpdateForm
    create_view_class = SourceCreateView
    url_prefix = 'searches'
    template_prefixes = (
        'localtv/admin/sources/searches/',
        'localtv/admin/sources/',
        'localtv/admin/',
    )

    def get_queryset(self):
        current_site = Site.objects.get_current()
        return SavedSearch.objects.filter(site=current_site)

    def get_list_view_kwargs(self):
        kwargs = super(SearchSection, self).get_list_view_kwargs()
        kwargs['queryset'] = kwargs['queryset'].annotate(
                                                    video_count=Count('video'))
        return kwargs

    def get_create_view_kwargs(self):
        kwargs = super(SearchSection, self).get_create_view_kwargs()
        kwargs.update({
            'import_task': search_update
        })
        return kwargs


class SourceSection(MiroCommunityAdminSection):
    url_prefix = 'sources'
    navigation_text = _('Sources')
    site_admin_required = True

    def __init__(self):
        self.subsections = [FeedSection(), SearchSection()]

    @property
    def urlpatterns(self):
        urlpatterns = patterns('')

        for section in self.subsections:
            urlpatterns += patterns('',
                url(r'^%s/' % section.url_prefix, include(section.urlpatterns))
            )
        return urlpatterns

    @property
    def pages(self):
        pages = ()
        for section in self.subsections:
            pages += section.pages
        return pages


registry.register(SourceSection)