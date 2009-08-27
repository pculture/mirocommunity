from datetime import datetime

from django.forms.formsets import DELETION_FIELD_NAME
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv import models
from localtv.subsite.admin import forms

@get_sitelocation
@require_site_admin
def bulk_edit(request, sitelocation=None):
    videos = models.Video.objects.filter(
        status=models.VIDEO_STATUS_ACTIVE,
        site=sitelocation.site).order_by('name')

    category = request.GET.get('category', '')
    try:
        category = int(category)
    except ValueError:
        category = ''

    if category != '':
        videos = videos.filter(categories__pk=category).distinct()

    formset = forms.VideoFormSet(queryset=videos)

    if request.method == 'POST':
        formset = forms.VideoFormSet(request.POST, request.FILES,
                                     queryset=videos)
        if formset.is_valid():
            for form in list(formset.deleted_forms):
                form.cleaned_data[DELETION_FIELD_NAME] = False
                form.instance.status = models.VIDEO_STATUS_REJECTED
                form.instance.save()
            bulk_edits = formset.extra_forms[0].cleaned_data
            for key in list(bulk_edits.keys()): # get the list because we'll be
                                                # changing the dictionary
                if not bulk_edits[key]:
                    del bulk_edits[key]
            bulk_action = request.POST.get('bulk_action', '')
            if bulk_action:
                bulk_edits['action'] = bulk_action
            if bulk_edits:
                for form in formset.initial_forms:
                    if not form.cleaned_data['bulk']:
                        continue
                    for key, value in bulk_edits.items():
                        if key == 'action': # do something to the video
                            if value == 'delete':
                                form.instance.status = \
                                    models.VIDEO_STATUS_REJECTED
                            elif value == 'unapprove':
                                form.instance.status = \
                                    models.VIDEO_STATUS_UNAPPROVED
                            elif value == 'feature':
                                form.instance.when_featured = datetime.now()
                        else:
                            form.cleaned_data[key] = value
            formset.forms = formset.initial_forms # get rid of the extra bulk
                                                  # edit form
            formset._deleted_forms = []
            formset.save()
            return HttpResponseRedirect(request.path)


    return render_to_response('localtv/subsite/admin/bulk_edit.html',
                              {'formset': formset,
                               'categories': models.Category.objects.filter(
                site=sitelocation.site)},
                              context_instance=RequestContext(request))
