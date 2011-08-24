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
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic.list_detail import object_list
from django.conf import settings
from django.utils.functional import curry

from tagging.models import Tag

import localtv.settings
from localtv.models import Video, Feed, Category
from localtv.search.forms import VideoSearchForm
from localtv.views import get_request_videos, get_featured_videos, get_latest_videos, get_popular_videos, get_tag_videos, get_category_videos, get_author_videos


VIDEOS_PER_PAGE = getattr(settings, 'VIDEOS_PER_PAGE', 15)
MAX_VOTES_PER_CATEGORY = getattr(settings, 'MAX_VOTES_PER_CATEGORY', 3)


#TODO: Replace this wrapper with a CBV when we move to Django 1.3
def video_list(func, object_name='videos'):
    def wrapper(request, *args, **kwargs):
        count = request.GET.get('count')
        if count:
            try:
                count = int(count)
            except ValueError:
                count = None
        if count is None:
            count = VIDEOS_PER_PAGE

        sort = request.GET.get('sort')
        if sort not in ('latest',):
            sort = None
        if sort:
            kwargs['sort'] = sort

        videos, template_name, extra_context = func(request, *args, **kwargs)
        return object_list(
            request=request, queryset=videos,
            paginate_by=count, template_name=template_name,
            allow_empty=True, template_object_name=object_name,
            extra_context=extra_context)
    return wrapper

category_list = curry(video_list, object_name="categories")



def index(request):
    return render_to_response(
        'localtv/browse.html', {},
        context_instance=RequestContext(request))


@video_list
def new_videos(request, sort=None):
    return get_latest_videos(request),
           'localtv/video_listing_new.html', None


@video_list
def this_week_videos(request, sort=None):
    videos = request_videos(request).filter(
        when_approved__gt=(datetime.datetime.now() - datetime.timedelta(days=7))
    ).order_by('-when_approved')

    return videos, 'localtv/video_listing_new.html', None


@video_list
def popular_videos(request, sort=None):
    # XXX: should the watch__timestamp__gte filter really be here? It should
    # probably either be removed or moved up into get_popular_videos.
    videos = get_popular_videos(request).filter(
        watch__timestamp__gte=datetime.datetime.now() - datetime.timedelta(7)
    )
    return videos, 'localtv/video_listing_popular.html', None

@video_list
def featured_videos(request, sort=None):
    videos = get_featured_videos(request)
    if sort == 'latest':
        videos = videos.with_best_date(
            request.sitelocation().use_original_date
        ).order_by = ('-best_date', '-last_featured')
    return videos, 'localtv/video_listing_featured.html', None

@video_list
def tag_videos(request, tag_name, sort=None):
    tag = get_object_or_404(Tag, name=tag_name)
    videos = get_tag_videos(tag)
    return videos, 'localtv/video_listing_tag.html', {'tag': tag}

@video_list
def feed_videos(request, feed_id, sort=None):
    feed = get_object_or_404(Feed, pk=feed_id,
                             site=request.sitelocation().site)
    videos = get_latest_videos(request).filter(feed=feed)
    return videos, 'localtv/video_listing_feed.html', {'feed': feed}


@video_list
def video_search(request, sort=None):

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
        videos = Video.objects.none()
    else:
        if sort == 'latest':
            videos = get_latest_videos(request).filter(pk__in=pks)
        else:
            videos = get_request_videos(request).filter(pk__in=pks)
            order = ['-localtv_video.id = %i' % int(pk) for pk in pks]
            videos = videos.extra(order_by=order)
    return videos, 'localtv/video_listing_search.html', {'query': query}

@category_list
def category_list(request, sort=None):
    categories = Category.objects.filter(
        site=request.sitelocation().site,
        parent=None)

    return categories, 'localtv/categories.html', None


@video_list
def category_videos(request, slug, sort=None):
    category = get_object_or_404(Category, slug=slug,
                                 site=request.sitelocation().site)

    user_can_vote = False
    
    videos = get_category_videos(request, category)

    if localtv.settings.voting_enabled() and category.contest_mode:
        user_can_vote = True
        if request.user.is_authenticated():
            import voting
            votes = voting.models.Vote.objects.filter(
                content_type=ContentType.objects.get_for_model(Video),
                object_id__in=videos.values_list('id', flat=True),
                user=request.user).count()
            if votes >= MAX_VOTES_PER_CATEGORY:
                user_can_vote = False
    return videos, 'localtv/category.html', {
        'category': category,
        'user_can_vote': user_can_vote
    }

def author_list(request):
    return render_to_response(
        'localtv/author_list.html',
        {'authors': User.objects.all()},
        context_instance=RequestContext(request)
    )

@video_list
def author_videos(request, author_id, sort='latest'):
    author = get_object_or_404(User, pk=author_id)
    videos = get_author_videos(request, author)
    if sort == 'latest':
        videos = videos.with_best_date(
            sitelocation.use_original_date
        ).order_by('-best_date')
    return videos, 'localtv/author.html', {'author': author}
