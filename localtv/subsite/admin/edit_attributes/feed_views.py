from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import simplejson

from localtv import models
from localtv.decorators import get_sitelocation, require_site_admin
from localtv.subsite.admin.edit_attributes import forms

@require_site_admin
@get_sitelocation
def edit_name(request, id, sitelocation=None):
    feed = get_object_or_404(
        models.Feed,
        id=id,
        site=sitelocation.site)

    edit_name_form = forms.FeedNameForm(request.POST)

    if edit_name_form.is_valid():
        feed.name = edit_name_form.cleaned_data.get('name')
        feed.save()

        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'SUCCESS',
                 'display_html': feed.name,
                 'input_html': 'I am input'}))

def edit_auto_categories(request):
    pass

def edit_auto_authors(request):
    pass
