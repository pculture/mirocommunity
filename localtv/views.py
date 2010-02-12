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
import urllib

from django.contrib.auth.models import User
from django.contrib import comments
from django.core.paginator import Paginator, InvalidPage
from django.core.urlresolvers import resolve, Resolver404
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.db.models import Q
from django.views.decorators.vary import vary_on_headers
from django.views.generic.list_detail import object_list

import haystack.forms

from localtv import models
from localtv.decorators import get_sitelocation
from localtv.admin import forms as admin_forms

@get_sitelocation
def index(request, sitelocation=None):
    featured_videos = models.Video.objects.filter(
        site=sitelocation.site_id,
        status=models.VIDEO_STATUS_ACTIVE,
        last_featured__isnull=False)
    featured_videos = featured_videos.order_by(
        '-last_featured', '-when_approved', '-when_published',
        '-when_submitted')

    popular_videos = models.Video.objects.popular_since(
        datetime.timedelta(days=7), sitelocation=sitelocation,
        status=models.VIDEO_STATUS_ACTIVE)

    new_videos = models.Video.objects.new(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)

    recent_comments = comments.get_model().objects.filter(
        site=sitelocation.site,
        is_removed=False,
        is_public=True).order_by('-submit_date')

    return render_to_response(
        'localtv/index.html',
        {'featured_videos': featured_videos,
         'popular_videos': popular_videos,
         'new_videos': new_videos,
         'comments': recent_comments},
        context_instance=RequestContext(request))


def about(request):
    return render_to_response(
        'localtv/about.html',
        {}, context_instance=RequestContext(request))


@vary_on_headers('User-Agent', 'Referer')
@get_sitelocation
def view_video(request, video_id, slug=None, sitelocation=None):
    video = get_object_or_404(models.Video, pk=video_id,
                              site=sitelocation.site)

    if video.status != models.VIDEO_STATUS_ACTIVE and \
            not sitelocation.user_is_admin(request.user):
        raise Http404

    if slug is not None and request.path != video.get_absolute_url():
        return HttpResponsePermanentRedirect(video.get_absolute_url())

    edit_video_form = None
    if sitelocation.user_is_admin(request.user):
        edit_video_form = admin_forms.EditVideoForm(instance=video)

    context = {'current_video': video,
               'edit_video_form': edit_video_form}

    if video.categories.count():
        category_obj = None
        referrer = request.META.get('HTTP_REFERER')
        host = request.META.get('HTTP_HOST')
        if referrer and host:
            if referrer.startswith('http://') or \
                    referrer.startswith('https://'):
                referrer = referrer[referrer.index('://')+3:]
            if referrer.startswith(host):
                referrer = referrer[len(host):]
                try:
                    view, args, kwargs = resolve(referrer)
                except Resolver404:
                    pass
                else:
                    if view == category:
                        try:
                            category_obj = models.Category.objects.get(
                                slug=args[0],
                                site=sitelocation.site)
                        except models.Category.DoesNotExist:
                            pass
                        else:
                            if not video.categories.filter(
                                pk=category_obj.pk).count():
                                category_obj = None

        if category_obj is None:
            category_obj = video.categories.all()[0]

        context['category'] = category_obj
        context['popular_videos'] = models.Video.objects.popular_since(
            datetime.timedelta(days=7),
            sitelocation=sitelocation,
            status=models.VIDEO_STATUS_ACTIVE,
            categories__pk=category_obj.pk).distinct()
    else:
        context['popular_videos'] = models.Video.objects.popular_since(
            datetime.timedelta(days=7),
            sitelocation=sitelocation,
            status=models.VIDEO_STATUS_ACTIVE)
    models.Watch.add(request, video)

    return render_to_response(
        'localtv/view_video.html',
        context,
        context_instance=RequestContext(request))

@get_sitelocation
def video_search(request, sitelocation=None):
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

    paginator = Paginator(results, 10)

    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404("No such page of results!")

    context = { # mimic the object_list context
        'form': form,
        'page_obj': page,
        'video_list': [result.object for result in page.object_list if result],
        'paginator': paginator,
        'pagetabs_args': urllib.urlencode({'q': query}),
        'query': query,
    }

    return render_to_response('localtv/video_listing_search.html', context,
                              context_instance=RequestContext(request))

@get_sitelocation
def category(request, slug=None, sitelocation=None):
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
            paginate_by=15,
            template_name='localtv/category.html',
            allow_empty=True, template_object_name='video',
            extra_context={'category': category})

@get_sitelocation
def author(request, id=None, sitelocation=None):
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
                           paginate_by=15,
                           template_name='localtv/author.html',
                           allow_empty=True,
                           template_object_name='video',
                           extra_context={'author': author})

@get_sitelocation
def share_email(request, content_type_pk, object_id, sitelocation):
    from email_share import views
    return views.share_email(request, content_type_pk, object_id,
                             {'site': sitelocation.site,
                              'sitelocation': sitelocation})
