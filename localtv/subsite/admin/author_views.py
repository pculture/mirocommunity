from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from localtv.decorators import get_sitelocation, require_site_admin
from localtv.subsite.admin import forms

@require_site_admin
@get_sitelocation
def authors(request, sitelocation=None):
    authors = User.objects.all()
    for author in authors:
        author.form = forms.AuthorForm(prefix="edit_%s" % author.id,
                                           instance=author)
    add_author_form = UserCreationForm()
    if request.method == 'GET':
        return render_to_response('localtv/subsite/admin/authors.html',
                                  {'authors': authors,
                                   'add_author_form': add_author_form},
                                  context_instance=RequestContext(request))
    else:
        if request.POST['submit'] == 'Add':
            add_author_form = UserCreationForm(request.POST)
            if add_author_form.is_valid():
                try:
                    add_author_form.save()
                except IntegrityError:
                    add_author_form._errors = \
                        'There was an error adding this author.  Does it '\
                        'already exist?'
                else:
                    return HttpResponseRedirect(request.path)

            return render_to_response('localtv/subsite/admin/authors.html',
                                      {'authors': authors,
                                       'add_author_form': add_author_form},
                                      context_instance=RequestContext(request))
        elif request.POST['submit'] == 'Save':
            invalid = False
            for author in authors:
                author.form = forms.AuthorForm(
                    request.POST,
                    request.FILES,
                    prefix="edit_%s" % author.id,
                    instance=author)
                if author.form.is_valid():
                    try:
                        author.form.save()
                    except IntegrityError:
                        author.form._errors = \
                            'There was an error editing %s. Does it already '\
                            'exist?' % author.name
                        invalid = True
                else:
                    invalid = True
            if invalid:
                return render_to_response(
                    'localtv/subsite/admin/authors.html',
                    {'authors': authors,
                     'add_author_form': add_author_form},
                    context_instance=RequestContext(request))
            else:
                return HttpResponseRedirect(request.path)
    return HttpResponseRedirect(request.path)

@require_site_admin
@get_sitelocation
def delete(request, sitelocation=None):
    author = get_object_or_404(User, pk=request.GET.get('id'))
    author.delete()
    return HttpResponseRedirect(reverse('localtv_admin_authors'))
