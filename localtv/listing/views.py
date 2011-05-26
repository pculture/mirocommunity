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
from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic.list_detail import object_list
from django.conf import settings

from tagging.models import Tag

from localtv import models
from localtv.search.forms import VideoSearchForm

def count_or_default(count):
    if count is None:
        count = getattr(settings, 'VIDEOS_PER_PAGE', 15)
    return count

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

def index(request):
    return render_to_response(
        'localtv/browse.html', {},
        context_instance=RequestContext(request))

@get_args
def new_videos(request, count=None, sort=None):
    count = count_or_default(count)

    videos = models.Video.objects.new(
        site=request.sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)
    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_new.html',
        allow_empty=True, template_object_name='video')

@get_args
def this_week_videos(request, count=None, sort=None):
    count = count_or_default(count)

    videos = models.Video.objects.filter(
        status=models.VIDEO_STATUS_ACTIVE,
        when_approved__gt=(datetime.datetime.utcnow() - datetime.timedelta(days=7))
        ).order_by('-when_approved')

    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_new.html',
        allow_empty=True, template_object_name='video')

@get_args
def popular_videos(request, count=None, sort=None):
    count = count_or_default(count)

    period = datetime.timedelta(days=7)
    videos = models.Video.objects.popular_since(
        period, request.sitelocation,
        watch__timestamp__gte=datetime.datetime.now() - period,
        status=models.VIDEO_STATUS_ACTIVE,
        )
    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_popular.html',
        allow_empty=True, template_object_name='video')

@get_args
def featured_videos(request, count=None, sort=None):
    count = count_or_default(count)

    kwargs = {
        'site': request.sitelocation.site,
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
def tag_videos(request, tag_name, count=None, sort=None):
    count = count_or_default(count)

    tag = get_object_or_404(Tag, name=tag_name)
    videos = models.Video.tagged.with_all(tag).filter(
        site=request.sitelocation.site,
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
def feed_videos(request, feed_id, count=None, sort=None):
    count = count_or_default(count)

    feed = get_object_or_404(models.Feed, pk=feed_id,
                             site=request.sitelocation.site)
    videos = models.Video.objects.new(site=request.sitelocation.site,
                                      feed=feed,
                                      status=models.VIDEO_STATUS_ACTIVE)
    return object_list(
        request=request, queryset=videos,
        paginate_by=count,
        template_name='localtv/video_listing_feed.html',
        allow_empty=True, template_object_name='video',
        extra_context={'feed': feed})


@get_args
def video_search(request, count=None, sort=None):
    count = count_or_default(count)

    query = ''
    pks = []

    if 'query' in request.GET and 'q' not in request.GET:
        # old-style templates
        GET = request.GET.copy()
        GET['q'] = GET['query']
        request.GET = GET

    if request.GET.get('q'):
        form = VideoSearchForm(request.GET)

        if form.is_valid():
            query = form.cleaned_data['q']
            results = form.search()
            pks = [result.pk for result in results if result is not None]

    if not pks:
        queryset = models.Video.objects.none()
    elif sort == 'latest':
        queryset = models.Video.objects.new(
            site=request.sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE,
            pk__in=pks)
    else:
        queryset = models.Video.objects.filter(
                site=request.sitelocation.site,
                status=models.VIDEO_STATUS_ACTIVE,
                pk__in=pks).order_by()
        order = ['-localtv_video.id = %i' % int(pk) for pk in pks]
        queryset = queryset.extra(order_by=order)
    return object_list(
        request=request, queryset=queryset,
        paginate_by=count,
        template_name='localtv/video_listing_search.html',
        allow_empty=True, template_object_name='video',
        extra_context={'query': query})

@get_args
def category(request, slug=None, count=None, sort=None):
    count = count_or_default(count)

    if slug is None:
        categories = models.Category.objects.filter(
            site=request.sitelocation.site,
            parent=None)

        return object_list(
            request=request, queryset=categories,
            paginate_by=count,
            template_name='localtv/categories.html',
            allow_empty=True, template_object_name='category')
    else:
        category = get_object_or_404(models.Category, slug=slug,
                                     site=request.sitelocation.site)
        return object_list(
            request=request, queryset=category.approved_set.all(),
            paginate_by=count,
            template_name='localtv/category.html',
            allow_empty=True, template_object_name='video',
            extra_context={'category': category})

@get_args
def author(request, id=None, count=None, sort=True):
    count = count_or_default(count)

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
            site=request.sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE).distinct()
        # Calls to DISTINCT in SQL can mess up the ordering. So,
        # if sorting is enabled, re-do the sort at the last minute.
        if sort:
            videos = videos.order_by('-best_date')
        return object_list(request=request, queryset=videos,
                           paginate_by=count,
                           template_name='localtv/author.html',
                           allow_empty=True,
                           template_object_name='video',
                           extra_context={'author': author})
