import urllib

from django.contrib import auth
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from django_openidconsumer import views as openidconsumer_views

from localtv import models
from localtv.openid import forms

 
def redirect_to_login_or_register(request, identity_url, openid_response):
    openidconsumer_views.default_on_success(
        request, identity_url, openid_response)
    reverse_url = reverse('localtv_openid_login_or_register')
    if request.GET.get('next'):
        reverse_url += '?' + urllib.urlencode({'next': request.GET['next']})
    return HttpResponseRedirect(reverse_url)


def login_and_redirect(request, user):
    if user.is_active:
        auth.login(request, user)

        if request.GET.get('next'):
            return HttpResponseRedirect(request.GET['next'])
        else:
            return HttpResponseRedirect('/')
    else:
        return render_to_response(
            'localtv/openid/rejected.html', {},
            context_instance=RequestContext(request))

def signout(request):
    auth.logout(request)
    return openidconsumer_views.signout(request)


def login_or_register(request):
    session_openids = request.session.get('openids')
    if not session_openids:
        return HttpResponseRedirect(reverse('localtv_openid_start'))

    # We do this outside of the GET method because we want to also
    # make sure we're not re-registering users (so, even during the
    # POST)
    try:
        localtv_openid = models.OpenIdUser.objects.get(
            url=session_openids[-1].openid)
    except models.OpenIdUser.DoesNotExist:
        pass
    else:
        user = auth.authenticate(openid_user=localtv_openid)
        return login_and_redirect(request, user)


    session_openid = session_openids[-1]
    if request.method == 'GET':
        registration_form = forms.OpenIdRegistrationForm()
        registration_form.initial['email'] = session_openid.sreg.get(
            'email', '')
        registration_form.initial['nickname'] = session_openid.sreg.get(
            'nickname', '')
        return render_to_response(
            'localtv/openid/register_form.html',
            {'registration_form': registration_form},
            context_instance=RequestContext(request))
    else:
        registration_form = forms.OpenIdRegistrationForm(request.POST)
        if registration_form.is_valid():
            user = auth.models.User.objects.create_user(
                registration_form.cleaned_data['nickname'],
                registration_form.cleaned_data['email'])

            localtv_openid = models.OpenIdUser(
                url=session_openid.openid,
                user = user)
            localtv_openid.save()

            return login_and_redirect(request, user)

        else:
            return render_to_response(
                'localtv/openid/register_form.html',
                {'registration_form': registration_form},
                context_instance=RequestContext(request))
