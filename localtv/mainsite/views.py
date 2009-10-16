from __future__ import with_statement
import os.path
import subprocess
import sys

from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.http import Http404
from django.conf import settings
from django.shortcuts import render_to_response

class SignupForm(UserCreationForm):
    url = forms.RegexField(r'^[A-Za-z0-9]\w*$',
                           help_text='.mirocommunity.org')
    email = forms.EmailField()

    def validate_unique(self):
        pass

    def clean_username(self):
        return self.cleaned_data['username']

    def clean_url(self):
        url = self.cleaned_data['url']
        if os.path.exists(os.path.join(
                settings.PROJECT_ROOT,
                '%s_project' % url)):
            raise forms.ValidationError('That project is already created.')
        return url

def signup_for_site(request):
    if not getattr(settings, 'PROJECT_ROOT', None) or \
            not getattr(settings, 'PROJECT_SCRIPT', None):
        raise Http404

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            with file(
                os.path.join(settings.PROJECT_ROOT,
                             '%(url)s.txt' % form.cleaned_data), 'a') as out:
                subprocess.check_call([settings.PROJECT_SCRIPT,
                                       form.cleaned_data['url']],
                                      stdout=out,
                                      env={
                        'DJANGO_SETTINGS_MODULE':
                            os.environ['DJANGO_SETTINGS_MODULE'],
                        'NEW_USERNAME': form.cleaned_data['username'],
                        'NEW_PASSWORD': form.cleaned_data['password1'],
                        'NEW_EMAIL': form.cleaned_data['email']})
                return render_to_response(
                    'localtv/mainsite/signup_thanks.html',
                    {'form': form})

    else:
        form = SignupForm()


    return render_to_response('localtv/mainsite/signup.html',
                              {'form': form})
