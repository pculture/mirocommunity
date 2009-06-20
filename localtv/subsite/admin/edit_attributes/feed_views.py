from django.http import (
    HttpResponse, HttpResponseBadRequest, HttpResponseRedirect)

import simplejson

def edit_name(request):
    return HttpResponse(
        simplejson.dumps(
            {'post_status': 'SUCCESS',
             'display_html': 'I am title',
             'input_html': 'I am input'}))

def edit_auto_categories(request):
    pass

def edit_auto_authors(request):
    pass
