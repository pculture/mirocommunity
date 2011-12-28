# Copyright 2010 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

from django import forms
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.urlresolvers import resolve
from django.http import Http404


class FlatPageForm(forms.ModelForm):
    content = FlatPage._meta.get_field('content').formfield(
                               help_text="This is everything you want to "
                                         "appear on the page.  The header and "
                                         "footer of your site will be "
                                         "automatically included.  This can "
                                         "contain HTML.")

    class Meta:
        model = FlatPage
        fields = ('url', 'title', 'content')

    def clean_url(self):
        url = self.cleaned_data['url']

        # Clean up the url with prepended and appended slashes.
        if not url.startswith('/'):
            url = '/' + url
        if getattr(settings, 'APPEND_SLASH', False) and not url.endswith('/'):
            url = url + '/'

        not_unique = FlatPage.objects.filter(
            url=url,
            sites=Site.objects.get_current()
        ).exclude(
            pk=self.instance.pk
        ).exists()

        if not_unique:
            raise ValidationError(
                'Flatpage with that URL already exists.')
        try:
            resolve(url)
        except Http404:
            pass # good, the URL didn't resolve
        else:
            raise ValidationError(
                'View with that URL already exists.')
        return url

    def save(self, commit=True):
        """On creation, adds the current site to the instance's sites."""
        created = self.instance.pk is None
        instance = super(FlatPageForm, self).save(commit)

        if created:
            if commit:
                instance.sites.add(Site.objects.get_current())
            else:
                old_save_m2m = self.save_m2m
                def save_m2m():
                    instance.sites.add(Site.objects.get_current())
                    old_save_m2m()
                self.save_m2m = save_m2m
        return instance
