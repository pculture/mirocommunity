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

import datetime

from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic.list_detail import object_list

from tagging.models import Tag

import haystack.forms

from localtv import models
from localtv.decorators import get_sitelocation

def get_count(func):
    def wrapper(request, *args, **kwargs):
        count = request.GET.get('count')
        if count:
            try:
                count = int(count)
            except ValueError:
                count = None
        if count is not None:
            kwargs['count'] = count
        return func(request, *args, **kwargs)
    return wrapper

@get_sitelocation
def index(request, sitelocation=None):
    return render_to_response(
        'localtv/browse.html', {},
        context_instance=RequestContext(request))

@get_count
@get_sitelocation
def new_videos(request, sitelocation=None, count=15):
    videos = models.Video.objects.new(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)
    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_new.html',
        allow_empty=True, template_object_name='video')

@get_count
@get_sitelocation
def popular_videos(request, sitelocation=None, count=15):
    period = datetime.timedelta(days=7)
    videos = models.Video.objects.popular_since(
        period, sitelocation,
        watch__timestamp__gte=datetime.datetime.now() - period,
        status=models.VIDEO_STATUS_ACTIVE,
        )
    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_popular.html',
        allow_empty=True, template_object_name='video')

@get_count
@get_sitelocation
def featured_videos(request, sitelocation=None, count=15):
    videos = models.Video.objects.filter(
        site=sitelocation.site, last_featured__isnull=False,
        status=models.VIDEO_STATUS_ACTIVE)
    videos = videos.order_by(
        '-last_featured', '-when_approved', '-when_published',
        '-when_submitted')
    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_featured.html',
        allow_empty=True, template_object_name='video')

@get_count
@get_sitelocation
def tag_videos(request, tag_name, sitelocation=None, count=15):
    tag = get_object_or_404(Tag, name=tag_name)
    videos = models.Video.tagged.with_all(tag).filter(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)
    videos = videos.order_by(
        '-when_approved', '-when_published', '-when_submitted')
    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_tag.html',
        allow_empty=True, template_object_name='video',
        extra_context={'tag': tag})

@get_count
@get_sitelocation
def feed_videos(request, feed_id, sitelocation=None, count=15):
    feed = get_object_or_404(models.Feed, pk=feed_id,
                             site=sitelocation.site)
    videos = models.Video.objects.new(site=sitelocation.site,
                                      feed=feed,
                                      status=models.VIDEO_STATUS_ACTIVE)
    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_feed.html',
        allow_empty=True, template_object_name='video',
        extra_context={'feed': feed})


@get_count
@get_sitelocation
def video_search(request, sitelocation=None, count=10):
    query = ''
    results = []

    if 'query' in request.GET and 'q' not in request.GET:
        # old-style templates
        GET = request.GET.copy()
        GET['q'] = GET['query']
        request.GET = GET

    if request.GET.get('q'):
        form = haystack.forms.ModelSearchForm(request.GET, load_all=True)

        if form.is_valid():
            query = form.cleaned_data['q']
            results = form.search()
    else:
        form = haystack.forms.ModelSearchForm()

    paginator = Paginator(results, count)

    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404("No such page of results!")

    context = { # mimic the object_list context
        'form': form,
        'page_obj': page,
        'video_list': [result.object for result in page.object_list if result],
        'paginator': paginator,
        'query': query,
    }

    return render_to_response('localtv/video_listing_search.html', context,
                              context_instance=RequestContext(request))

@get_count
@get_sitelocation
def category(request, slug=None, sitelocation=None, count=15):
    if slug is None:
        categories = models.Category.objects.filter(
            site=sitelocation.site,
            parent=None)

        return object_list(
            request=request, queryset=categories,
            paginate_by=18,
            template_name='localtv/categories.html',
            allow_empty=True, template_object_name='category')
    else:
        category = get_object_or_404(models.Category, slug=slug,
                                     site=sitelocation.site)
        return object_list(
            request=request, queryset=category.approved_set.all(),
            paginate_by=count,
            template_name='localtv/category.html',
            allow_empty=True, template_object_name='video',
            extra_context={'category': category})

@get_count
@get_sitelocation
def author(request, id=None, sitelocation=None, count=15):
    if id is None:
        return render_to_response(
            'localtv/author_list.html',
            {'authors': User.objects.all()},
            context_instance=RequestContext(request))
    else:
        author = get_object_or_404(User,
                                   pk=id)
        videos = models.Video.objects.filter(
            Q(authors=author) | Q(user=author),
            site=sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE).distinct()
        return object_list(request=request, queryset=videos,
                           paginate_by=count,
                           template_name='localtv/author.html',
                           allow_empty=True,
                           template_object_name='video',
                           extra_context={'author': author})
