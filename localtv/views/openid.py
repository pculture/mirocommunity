import urllib

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _

from django_openidconsumer import views as openidconsumer_views

from localtv import models
from localtv import forms

 
def redirect_to_login_or_register(request, identity_url, openid_response):
    openidconsumer_views.default_on_success(
        request, identity_url, openid_response)
    reverse_url = reverse('localtv_openid_login_or_register')
    if request.GET.get('next'):
        reverse_url += '?' + urllib.urlencode({'next': request.GET['next']})
    return HttpResponseRedirect(reverse_url)


def login_or_register(request):
    session_openids = request.session.get('openids')
    if not session_openids:
        return HttpResponseRedirect(reverse('localtv_openid_start'))

    session_openid = session_openids[-1]
    if request.method == 'GET':
        registration_form = forms.OpenIdRegistrationForm()

        try:
            localtv_openid = models.OpenIdUser.objects.get(
                url=session_openids[-1].openid)

            if localtv_openid.status == models.OPENID_STATUS_ACTIVE:
                request.session.set('openid_localtv', localtv_openid)
                if request.GET.get('next'):
                    return HttpResponseRedirect(request.GET['next'])
                else:
                    return HttpResponseRedirect('/')
            else:
                return render_to_response(
                    'localtv/openid/rejected.html')
        except models.OpenIdUser.DoesNotExist:
            # it's cool, we'll just give them a registration form then
            pass

        registration_form = forms.OpenIdRegistrationForm()
        registration_form.initial['email'] = session_openid.attrs.get(
            'email', '')
        registration_form.initial['nickname'] = session_openid.attrs.get(
            'nickname', '')
        return render_to_response(
            'localtv/openid/register_form.html',
            {'registration_form': registration_form})
    else:
        # yikes!  Put post stuff here
        pass
    

def complete(request):
    import pdb
    pdb.set_trace()

    # try to get the model out of the database
    session_openids = request.session.get('openids')
    if not session_openids:
        return HttpResponseRedirect(reverse('localtv_openid_start'))

    try:
        localtv_openid = models.OpenIdUser.objects.get(
            url=session_openids[-1].openid)
    except models.OpenIdUser.DoesNotExist:
        reverse_url = reverse('localtv_openid_register')
        if request.GET.get('next'):
            reverse_url += + '?' + urllib.urlencode(
                {'next': request.GET['next']})
        return HttpResponseRedirect(reverse_url)
    
    if localtv_openid.status == models.OPENID_STATUS_ACTIVE:
        request.session.set('openid_localtv', localtv_openid)
        if request.GET.get('next'):
            return HttpResponseRedirect(request.GET['next'])
        else:
            return HttpResponseRedirect('/')
    else:
        return render_to_response(
            'localtv/openid/rejected.html')


def register(request):
    session_openids = request.session.get('openids')
    if not session_openids:
        return HttpResponseRedirect(reverse('localtv_openid_start'))

    session_openid = session_openids[-1]
    if models.OpenIdUser.objects.count(url=session_openids[-1].openid):
        if request.GET.get('next'):
            return HttpResponseRedirect(request.GET['next'])
        else:
            return HttpResponse(
                _("User already registered"))
    else:
        if request.method == 'GET':
            registration_form = forms.OpenIdRegistrationForm()
            import pdb
            pdb.set_trace()
            # set initial data here
        else:
            registration_form = forms.OpenIdRegistrationForm(request.POST)

