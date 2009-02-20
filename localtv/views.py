from django.contrib.sites.models import Site
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response

def subsite_index(request):
    current_site = Site.objects.get_current()
    return HttpResponse('subsite: %s' % current_site.name)
