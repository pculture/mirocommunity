from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.subsite.admin import forms

@require_site_admin
@get_sitelocation
def users(request, sitelocation=None):
    admins = sitelocation.admins_user.all()
    if request.method == 'POST':
        if request.POST['submit'] == 'Add':
            add_user_form = forms.AddUserForm(request.POST)
            if add_user_form.is_valid():
                users = add_user_form.cleaned_data['user']
                sitelocation.admins_user.add(*users)
                return HttpResponseRedirect(request.path)

            return render_to_response('localtv/subsite/admin/users.html',
                                      {'admins': admins,
                                       'add_user_form': add_user_form},
                                      context_instance=RequestContext(request))
        elif request.POST['submit'] == 'Delete':
            user_id = request.POST.get('id')
            if user_id is not None:
                try:
                    user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    pass
                else:
                    sitelocation.admins_user.remove(user)
            return HttpResponseRedirect(request.path)
        else:
            return HttpResponseRedirect(request.path)
    else:
        add_user_form = forms.AddUserForm()
        return render_to_response('localtv/subsite/admin/users.html',
                                  {'admins': admins,
                                   'add_user_form': add_user_form},
                                  context_instance=RequestContext(request))
