import urllib
import datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.db.models import Q
from django.views.generic.list_detail import object_list

from localtv import models
from localtv.decorators import get_sitelocation
from localtv.subsite.admin import forms as admin_forms


@get_sitelocation
def subsite_index(request, sitelocation=None):
    featured_videos = models.Video.objects.filter(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE,
        last_featured__isnull=False)
    featured_videos = featured_videos.order_by(
        '-last_featured', '-when_approved', '-when_submitted')[:10]
    new_videos = models.Video.objects.filter(
        site=sitelocation.site,
        status=models.VIDEO_STATUS_ACTIVE)
    new_videos = new_videos.order_by(
        '-when_approved', '-when_submitted')[:10]

    return render_to_response(
        'localtv/subsite/index.html',
        {'sitelocation': sitelocation,
         'request': request,
         'featured_videos': featured_videos,
         'new_videos': new_videos},
        context_instance=RequestContext(request))


@get_sitelocation
def view_video(request, video_id, sitelocation=None):
    video = get_object_or_404(models.Video, pk=video_id, site=sitelocation.site)

    edit_video_form = None
    openid_user = request.session.get('openid_localtv')
    if openid_user and openid_user.admin_for_sitelocation(sitelocation):
        edit_video_form = admin_forms.EditVideoForm.create_from_video(video)

    models.Watch.add(request, video, openid_user)

    return render_to_response(
        'localtv/subsite/view_video.html',
        {'sitelocation': sitelocation,
         'current_video': video,
         'popular_videos': models.Video.popular_since(datetime.timedelta(
                    days=1), sitelocation=sitelocation)[:9],
         'intensedebate_acct': getattr(
                settings, 'LOCALTV_INTENSEDEBATE_ACCT', None),
         'edit_video_form': edit_video_form},
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

        for term in include_terms:
            videos = videos.filter(
                Q(description__icontains=term) | Q(name__icontains=term))

        for term in stripped_exclude_terms:
            videos = videos.exclude(
                Q(description__icontains=term) | Q(name__icontains=term))

        return object_list(
            request=request, queryset=videos,
            paginate_by=5,
            template_name='localtv/subsite/video_listing.html',
            allow_empty=True, template_object_name='video',
            extra_context={
                'pagetabs_url': reverse('localtv_subsite_search'),
                'pagetabs_args': urllib.urlencode({'query': query_string})})

    else:
        return render_to_response(
            'localtv/subsite/video_listing_search.html', {},
            context_instance=RequestContext(request))

        
