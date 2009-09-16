from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms.formsets import DELETION_FIELD_NAME
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.subsite.admin import forms

@require_site_admin
@get_sitelocation
def users(request, sitelocation=None):
    formset = forms.AuthorFormSet(queryset=User.objects.all())
    add_user_form = forms.AuthorForm()
    if request.method == 'POST':
        if request.POST['submit'] == 'Add':
            add_user_form = forms.AuthorForm(request.POST)
            if add_user_form.is_valid():
                user = add_user_form.save()
                return HttpResponseRedirect(request.path)
        elif request.POST['submit'] == 'Delete':
            user_id = request.POST.get('id')
            if user_id is not None:
                try:
                    user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    pass
                else:
                    sitelocation.admins.remove(user)
            return HttpResponseRedirect(request.path)
        elif request.POST['submit'] == 'Save':
            formset = forms.AuthorFormSet(request.POST, request.FILES,
                                          queryset=User.objects.all())
            if formset.is_valid():
                formset.save()
                return HttpResponseRedirect(request.path)
        else:
            return HttpResponseRedirect(request.path)

    return render_to_response('localtv/subsite/admin/users.html',
                              {'formset': formset,
                               'add_user_form': add_user_form},
                              context_instance=RequestContext(request))
