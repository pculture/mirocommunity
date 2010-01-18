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

import urllib
import datetime

from django.contrib.auth.models import User
from django.contrib import comments
from django.core.urlresolvers import reverse, resolve, Resolver404
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.db.models import Q
from django.views.decorators.vary import vary_on_headers
from django.views.generic.list_detail import object_list

import tagging

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
    query_string = request.GET.get('query', '')

    if query_string:
        terms = set(query_string.split())

        exclude_terms = set([
                component for component in terms if component.startswith('-')])
        include_terms = terms.difference(exclude_terms)
        stripped_exclude_terms = [term.lstrip('-') for term in exclude_terms]

        videos = models.Video.objects.filter(
            site=sitelocation.site,
            status=models.VIDEO_STATUS_ACTIVE)

        include_tags = tagging.utils.get_tag_list(list(include_terms))
        exclude_tags = tagging.utils.get_tag_list(list(exclude_terms))
        included_videos = models.Video.tagged.with_any(include_tags)
        excluded_videos = models.Video.tagged.with_any(exclude_tags)

        for term in include_terms:
            videos = videos.filter(
                Q(description__icontains=term) | Q(name__icontains=term) |
                Q(pk__in=included_videos) |
                Q(categories__name__icontains=term) |
                Q(user__username__icontains=term) |
                Q(user__first_name__icontains=term) |
                Q(user__last_name__icontains=term) |
                Q(video_service_user__icontains=term) |
                Q(feed__name__icontains=term))

        for term in stripped_exclude_terms:
            videos = videos.exclude(description__icontains=term)
            videos = videos.exclude(name__icontains=term)
            videos = videos.exclude(pk__in=excluded_videos)
            videos = videos.exclude(categories__name__icontains=term)
            videos = videos.exclude(user__username__icontains=term)
            videos = videos.exclude(user__first_name__icontains=term)
            videos = videos.exclude(user__last_name__icontains=term)
            videos = videos.exclude(video_service_user__icontains=term)
            videos = videos.exclude(feed__name__icontains=term)

        videos = videos.distinct()

        return object_list(
            request=request, queryset=videos,
            paginate_by=5,
            template_name='localtv/video_listing_search.html',
            allow_empty=True, template_object_name='video',
            extra_context={
                'pagetabs_url': reverse('localtv_search'),
                'pagetabs_args': urllib.urlencode(
                    {'query': query_string.encode('utf8')})})

    else:
        return render_to_response(
            'localtv/video_listing_search.html', {},
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
        return render_to_response(
            'localtv/category.html',
            {'category': get_object_or_404(models.Category, slug=slug,
                                           site=sitelocation.site)},
            context_instance=RequestContext(request))


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
        return render_to_response(
            'localtv/author.html',
            {'author': author,
             'video_list': videos},
            context_instance=RequestContext(request))


@get_sitelocation
def share_email(request, content_type_pk, object_id, sitelocation):
    from email_share import views
    return views.share_email(request, content_type_pk, object_id,
                             {'site': sitelocation.site,
                              'sitelocation': sitelocation})
