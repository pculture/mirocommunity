from django.db.models import Count
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.subsite.admin import forms
from localtv.util import sort_header

@require_site_admin
@get_sitelocation
def users(request, sitelocation=None):
    sort = request.GET.get('sort', 'username')
    headers = [
        sort_header('username', 'Username', sort),
        {'label': 'Name'},
        {'label': 'Email'},
        {'label': 'OpenID'},
        {'label': 'Role'},
        {'label': 'Thumbnail'},
        {'label': 'Description'},
        sort_header('authored_set__count', 'Videos', sort)
        ]
    users = User.objects.all().annotate(Count('authored_set')).order_by(sort)
    formset = forms.AuthorFormSet(queryset=users)
    add_user_form = forms.AuthorForm()
    if request.method == 'POST':
        if request.POST['submit'] == 'Add':
            add_user_form = forms.AuthorForm(request.POST, request.FILES)
            if add_user_form.is_valid():
                user = add_user_form.save()
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
                               'add_user_form': add_user_form,
                               'headers': headers},
                              context_instance=RequestContext(request))
