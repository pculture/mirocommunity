from django.http import Http404, HttpResponse
from django.contrib.sites.models import Site

from localtv.models import SiteLocation

def create_site(request):
    if request.method != 'POST':
        raise Http404
    site_name = request.POST.get('site_name')
    if site_name is None:
        return HttpResponse('please include a site name')
    full_name = site_name + '.mirocommunity.org'
    if Site.objects.filter(domain=full_name).count():
        return HttpResponse('that domain already exists')
    site = Site(domain=full_name, name=site_name)
    site.save()
    site_location = SiteLocation(site=site)
    site_location.save()
    return HttpResponse('%s created.  Ask someone to set up a new Django project with SITE_ID=%i' % (
            full_name, site.id))
