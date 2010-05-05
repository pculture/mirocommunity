from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv.decorators import get_sitelocation

from localtv.user_profile import forms

@login_required
@get_sitelocation
def profile(request, sitelocation=None):
    if request.method == 'POST':
        form = forms.ProfileForm(request.POST, request.FILES,
                                 instance=request.user.get_profile())
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.path)
    else:
        form = forms.ProfileForm(instance=request.user.get_profile())

    return render_to_response('localtv/user_profile/edit.html',
                              {'form': form},
                              context_instance=RequestContext(request))

@login_required
@get_sitelocation
def notifications(request, sitelocation=None):
    if request.method == 'POST':
        form = forms.NotificationsForm(request.POST,
                                 instance=request.user)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.path)
    else:
        form = forms.NotificationsForm(instance=request.user)

    return render_to_response('localtv/user_profile/notifications.html',
                              {'form': form},
                              context_instance=RequestContext(request))
