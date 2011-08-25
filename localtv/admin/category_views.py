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

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

import localtv.settings
from localtv.decorators import require_site_admin
from localtv.models import Category, Video, SiteLocation
from localtv.util import MockQueryset
from localtv.admin import forms

@require_site_admin
@csrf_protect
def categories(request):
    sitelocation = SiteLocation.objects.get_current()
    categories = MockQueryset(Category.in_order(sitelocation.site))
    formset = forms.CategoryFormSet(queryset=categories)
    headers = [
        {'label': 'Category'},
        {'label': 'Description'},
        {'label': 'Slug'},
         {'label': 'Videos'}
        ]
    add_category_form = forms.CategoryForm()
    if request.method == 'POST':
        if not request.POST.get('form-TOTAL_FORMS'):
            category = Category(site=sitelocation.site)
            add_category_form = forms.CategoryForm(request.POST,
                                                   request.FILES,
                                                   instance=category)
            if add_category_form.is_valid():
                add_category_form.save()
                return HttpResponseRedirect(request.path + '?successful')

        else:
            formset = forms.CategoryFormSet(request.POST, request.FILES,
                                            queryset=categories)
            if formset.is_valid():
                formset.save()
                action = request.POST.get('bulk_action')
                if action == 'delete':
                    for data in  formset.cleaned_data:
                        if data['BULK']:
                            category = data['id']
                            for child in category.child_set.all():
                                # reset children to no parent
                                child.parent = None
                                child.save()
                            data['id'].delete()
                return HttpResponseRedirect(request.path + '?successful')

    return render_to_response('localtv/admin/categories.html',
                              {'formset': formset,
                               'headers': headers,
                               'add_category_form': add_category_form},
                              context_instance=RequestContext(request))


@require_site_admin
def votes(request, slug):
    if not localtv.settings.voting_enabled():
        raise Http404
    
    category = get_object_or_404(Category, slug=slug)

    def score_key((k, v)):
        return v['score']

    def sorted_scores():
        videos = category.approved_set.only('id')
        import voting
        scores = voting.models.Vote.objects.get_scores_in_bulk(videos)

        for video_pk, score_dict in sorted(scores.items(),
                                           key=score_key,
                                           reverse=True):
            yield Video.objects.get(pk=video_pk), score_dict

    return render_to_response('localtv/admin/category_votes.html',
                              {'category': category,
                               'sorted_scores': sorted_scores()
                               },
                              context_instance=RequestContext(request))
    
