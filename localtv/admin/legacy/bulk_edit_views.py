from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_protect

from localtv.decorators import require_site_admin
from localtv.models import Video, SiteSettings
from localtv.admin.legacy import forms
from localtv.utils import SortHeaders

@require_site_admin
@csrf_protect
def bulk_edit(request, formset_class=forms.VideoFormSet):
    if ('just_the_author_field' in request.GET and 'video_id' in request.GET):
        # generate just the particular form that the user wants
        template_data = {}
        form_prefix = request.GET['just_the_author_field']
        video = get_object_or_404(Video, pk=int(request.GET['video_id']))
        form = forms.BulkEditVideoForm(instance=video, prefix=form_prefix)
        template_data['form'] = form
        template = 'localtv/admin/bulk_edit_author_widget.html'
        return render_to_response(template,
                                  template_data,
                                  context_instance=RequestContext(request))

    site_settings = SiteSettings.objects.get_current()
    videos = Video.objects.filter(status=Video.PUBLISHED,
                                  site=site_settings.site)

    if 'filter' in request.GET:
        filter_type = request.GET['filter']
        if filter_type == 'featured':
            videos = videos.exclude(last_featured=None)
        elif filter_type == 'rejected':
            videos = Video.objects.filter(status=Video.HIDDEN)
        elif filter_type == 'no-attribution':
            videos = videos.filter(authors=None)
        elif filter_type == 'no-category':
            videos = videos.filter(categories=None)
        elif filter_type == 'unapproved':
            videos = Video.objects.filter(status=Video.NEEDS_MODERATION)

    videos = videos.select_related('feed', 'search', 'site')

    category = request.GET.get('category', '')
    try:
        category = int(category)
    except ValueError:
        category = ''

    if category != '':
        videos = videos.filter(categories__pk=category).distinct()

    author = request.GET.get('author', '')
    try:
        author = int(author)
    except ValueError:
        author = ''

    if author != '':
        videos = videos.filter(authors__pk=author).distinct()

    search_string = request.GET.get('q', '')
    if search_string != '':
        videos = videos.filter(
            Q(description__icontains=search_string) |
            Q(name__icontains=search_string) |
            Q(categories__name__icontains=search_string) |
            Q(user__username__icontains=search_string) |
            Q(user__first_name__icontains=search_string) |
            Q(user__last_name__icontains=search_string) |
            Q(video_service_user__icontains=search_string) |
            Q(feed__name__icontains=search_string)).distinct()

    headers = SortHeaders(request, (
            ('Video Title', 'name'),
            ('Source', 'source'),
            ('Categories', None),
            ('Date Published', '-when_published'),
            ('Date Imported', '-when_submitted'),
            ))

    sort = headers.order_by()
    if sort.endswith('source'):
        videos = videos.extra(select={
                'name_lower':'LOWER(localtv_video.name)'})
        videos = videos.order_by(sort.replace('source', 'calculated_source_type'))
    elif sort.endswith('name'):
        videos = videos.extra(select={
                'name_lower':'LOWER(localtv_video.name)'}).order_by(
            sort.replace('name', 'name_lower'))
    else:
        videos = videos.order_by(sort)
    video_paginator = Paginator(videos, 30)
    try:
        page = video_paginator.page(int(request.GET.get('page', 1)))
    except ValueError:
        return HttpResponseBadRequest('Not a page number')
    except EmptyPage:
        page = video_paginator.page(video_paginator.num_pages)

    if request.method == 'POST':
        formset = formset_class(request.POST, request.FILES,
                                queryset=page.object_list)
        if formset.is_valid():
            formset.save()
            if 'successful' in request.GET:
                path_with_success = request.get_full_path()
            else:
                path = request.get_full_path()
                if '?' in path:
                    path_with_success =  path + '&successful'
                else:
                    path_with_success = path + '?successful'

            return HttpResponseRedirect(path_with_success)
    else:
        formset = formset_class(queryset=page.object_list)

    return render_to_response('localtv/admin/bulk_edit.html',
                              {'formset': formset,
                               'headers': headers,
                               'search_string': search_string,
                               'page': page,
                               'categories': formset._qs_cache['categories'],
                               'users': formset._qs_cache['authors']},
                              context_instance=RequestContext(request))
