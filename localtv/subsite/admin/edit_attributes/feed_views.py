from django import template
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
                 'input_html': edit_name_form.as_ul()}))
    else:
        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'FAIL',
                 'display_html': feed.name,
                 'input_html': edit_name_form.as_ul()}))
        

@require_site_admin
@get_sitelocation
def edit_auto_categories(request, id, sitelocation=None):
    feed = get_object_or_404(
        models.Feed,
        id=id,
        site=sitelocation.site)

    edit_auto_categories_form = forms.FeedAutoCategoriesForm(request.POST)
    display_template = template.loader.get_template(
        'localtv/subsite/display_templates/feed_auto_categories.html')

    if edit_auto_categories_form.is_valid():
        feed.auto_categories.clear()
        for category in edit_auto_categories_form.cleaned_data.get(
                'auto_categories'):
            feed.auto_categories.add(category)

        feed.auto_categories = edit_auto_categories_form.cleaned_data.get(
            'auto_categories')
        feed.save()

        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'SUCCESS',
                 'display_html': display_template.render(
                        template.Context({'instance': feed})),
                 'input_html': edit_auto_categories_form.as_ul()}))
    else:
        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'FAIL',
                 'display_html': display_template.render(
                        template.Context({'instance': feed})),
                 'input_html': edit_auto_categories_form.as_ul()}))

@require_site_admin
@get_sitelocation
def edit_auto_authors(request, id, sitelocation=None):
    feed = get_object_or_404(
        models.Feed,
        id=id,
        site=sitelocation.site)

    edit_auto_authors_form = forms.FeedAutoAuthorsForm(request.POST)
    display_template = template.loader.get_template(
        'localtv/subsite/display_templates/feed_auto_authors.html')

    if edit_auto_authors_form.is_valid():
        feed.auto_authors.clear()
        for author in edit_auto_authors_form.cleaned_data.get(
                'auto_authors'):
            feed.auto_authors.add(author)

        feed.auto_authors = edit_auto_authors_form.cleaned_data.get(
            'auto_authors')
        feed.save()

        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'SUCCESS',
                 'display_html': display_template.render(
                        template.Context({'instance': feed})),
                 'input_html': edit_auto_authors_form.as_ul()}))
    else:
        return HttpResponse(
            simplejson.dumps(
                {'post_status': 'FAIL',
                 'display_html': display_template.render(
                        template.Context({'instance': feed})),
                 'input_html': edit_auto_authors_form.as_ul()}))
