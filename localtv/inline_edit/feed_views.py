# Copyright 2009 - Participatory Culture Foundation
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

from django import template
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import simplejson

from localtv import models
from localtv.decorators import get_sitelocation, require_site_admin
from localtv.inline_edit import forms

@require_site_admin
@get_sitelocation
def edit_auto_categories(request, id, sitelocation=None):
    feed = get_object_or_404(
        models.Feed,
        id=id,
        site=sitelocation.site)

    edit_auto_categories_form = forms.FeedAutoCategoriesForm(request.POST,
                                                             instance=feed)
    display_template = template.loader.get_template(
        'localtv/inline_edit/feed_auto_categories.html')

    if edit_auto_categories_form.is_valid():
        old_categories = list(feed.auto_categories.all())
        new_categories = edit_auto_categories_form.cleaned_data.get(
            'auto_categories')
        for video in feed.video_set.all():
            if list(video.categories.all()) == old_categories:
                video.categories = new_categories
                video.save()

        feed.auto_categories = new_categories
        feed.save()

        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'SUCCESS',
                 'display_html': display_template.render(
                        template.Context({'instance': feed})),
                 'input_html': edit_auto_categories_form.as_ul()}))
    else:
        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'FAIL',
                 'display_html': display_template.render(
                        template.Context({'instance': feed})),
                 'input_html': edit_auto_categories_form.as_ul()}))

@require_site_admin
@get_sitelocation
def edit_auto_authors(request, id, sitelocation=None):
    feed = get_object_or_404(
        models.Feed,
        id=id,
        site=sitelocation.site)

    edit_auto_authors_form = forms.FeedAutoAuthorsForm(request.POST,
                                                       instance=feed)
    display_template = template.loader.get_template(
        'localtv/inline_edit/feed_auto_authors.html')

    if edit_auto_authors_form.is_valid():
        old_authors = list(feed.auto_authors.all())
        new_authors = edit_auto_authors_form.cleaned_data.get(
            'auto_authors')
        for video in feed.video_set.all():
            if list(video.authors.all()) == old_authors:
                video.authors = new_authors
                video.save()

        feed.auto_authors = new_authors
        feed.save()

        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'SUCCESS',
                 'display_html': display_template.render(
                        template.Context({'instance': feed})),
                 'input_html': edit_auto_authors_form.as_ul()}))
    else:
        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'FAIL',
                 'display_html': display_template.render(
                        template.Context({'instance': feed})),
                 'input_html': edit_auto_authors_form.as_ul()}))
