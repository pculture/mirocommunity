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
import operator

from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic.list_detail import object_list

from tagging.models import Tag

import haystack.forms, haystack.query

from localtv import models, util
from localtv.decorators import get_sitelocation

def get_args(func):
    def wrapper(request, *args, **kwargs):
        count = request.GET.get('count')
        if count:
            try:
                count = int(count)
            except ValueError:
                count = None
        if count:
            kwargs['count'] = count
        sort = request.GET.get('sort')
        if sort not in ('latest',):
            sort = None
        if sort:
            kwargs['sort'] = sort
        return func(request, *args, **kwargs)
    return wrapper

@get_sitelocation
def index(request, sitelocation=None):
    return render_to_response(
        'localtv/browse.html', {},
        context_instance=RequestContext(request))

@get_args
@get_sitelocation
def new_videos(request, sitelocation=None, count=15, sort=None):
    videos = models.Video.objects.new(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)
    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_new.html',
        allow_empty=True, template_object_name='video')

@get_args
@get_sitelocation
def popular_videos(request, sitelocation=None, count=15, sort=None):
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

@get_args
@get_sitelocation
def featured_videos(request, sitelocation=None, count=15, sort=None):
    kwargs = {
        'site': sitelocation.site,
        'last_featured__isnull': False,
        'status': models.VIDEO_STATUS_ACTIVE}
    if sort == 'latest':
        videos = models.Video.objects.new(**kwargs)
    else:
        videos = models.Video.objects.filter(**kwargs)
        videos = videos.order_by(
            '-last_featured', '-when_approved', '-when_published',
            '-when_submitted')
    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_featured.html',
        allow_empty=True, template_object_name='video')

@get_args
@get_sitelocation
def tag_videos(request, tag_name, sitelocation=None, count=15, sort=None):
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

@get_args
@get_sitelocation
def feed_videos(request, feed_id, sitelocation=None, count=15, sort=None):
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


@get_args
@get_sitelocation
def video_search(request, sitelocation=None, count=10, sort=None):
    query = ''
    pks = []

    if 'query' in request.GET and 'q' not in request.GET:
        # old-style templates
        GET = request.GET.copy()
        GET['q'] = GET['query']
        request.GET = GET

    if request.GET.get('q'):
        form = haystack.forms.ModelSearchForm(
            request.GET,
            searchqueryset=haystack.query.RelatedSearchQuerySet())

        if form.is_valid():
            query = form.cleaned_data['q']
            results = form.search()
            pks = [result.pk for result in results if result is not None]
    else:
        form = haystack.forms.ModelSearchForm()
    if not pks:
        queryset = models.Video.objects.empty()
    elif sort == 'latest':
        queryset = models.Video.objects.new(
            site=sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE,
            pk__in=pks)
    else:
        queryset = models.Video.objects.filter(
                site=sitelocation.site,
                status=models.VIDEO_STATUS_ACTIVE,
                pk__in=pks).order_by()
        order = ['-localtv_video.id = %i' % pk for pk in pks]
        queryset = queryset.extra(order_by=order)
    return object_list(
        request=request, queryset=queryset,
        paginate_by=count,
        template_name='localtv/video_listing_search.html',
        allow_empty=True, template_object_name='video',
        extra_context={'query': query})

@get_args
@get_sitelocation
def category(request, slug=None, sitelocation=None, count=15, sort=None):
    if slug is None:
        categories = models.Category.objects.filter(
            site=sitelocation.site,
            parent=None)

        return object_list(
            request=request, queryset=categories,
            paginate_by=count,
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

@get_args
@get_sitelocation
def author(request, id=None, sitelocation=None, count=15, sort=None):
    if id is None:
        return render_to_response(
            'localtv/author_list.html',
            {'authors': User.objects.all()},
            context_instance=RequestContext(request))
    else:
        author = get_object_or_404(User,
                                   pk=id)
        if sort:
            videos = models.Video.objects.new()
        else:
            videos = models.Video.objects.all()
        videos = videos.filter(
            Q(authors=author) | Q(user=author),
            site=sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE).distinct()
        return object_list(request=request, queryset=videos,
                           paginate_by=count,
                           template_name='localtv/author.html',
                           allow_empty=True,
                           template_object_name='video',
                           extra_context={'author': author})
