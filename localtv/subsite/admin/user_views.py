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
    users = User.objects.all()
    formset = forms.AuthorFormSet(queryset=users)
    add_user_form = forms.AddUserForm()
    create_user_form = UserCreationForm()
    if request.method == 'POST':
        if request.POST['submit'] == 'Add':
            add_user_form = forms.AddUserForm(request.POST)
            if add_user_form.is_valid():
                users = add_user_form.cleaned_data['user']
                sitelocation.admins.add(*users)
                return HttpResponseRedirect(request.path)
        elif request.POST['submit'] == 'Create':
            create_user_form = UserCreationForm(request.POST)
            if create_user_form.is_valid():
                user = create_user_form.save()
                sitelocation.admins.add(user)
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
                                          queryset=users)
            if formset.is_valid():
                for form in list(formset.deleted_forms):
                    form.cleaned_data[DELETION_FIELD_NAME] = False
                    form.instance.is_active = False
                    sitelocation.site.admins.remove(form.instance)
                    form.instance.save()
                formset.save()
                return HttpResponseRedirect(request.path)
        else:
            return HttpResponseRedirect(request.path)

    return render_to_response('localtv/subsite/admin/users.html',
                              {'formset': formset,
                               'add_user_form': add_user_form,
                               'create_user_form': create_user_form},
                              context_instance=RequestContext(request))
