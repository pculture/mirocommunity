# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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

import datetime
import re
import os.path
import feedparser
import urlparse

import django.template.defaultfilters
from django import forms
from django.forms.formsets import BaseFormSet
from django.forms.models import modelformset_factory, BaseModelFormSet, \
    construct_instance
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.urlresolvers import resolve
from django.http import Http404
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from tagging.forms import TagField

import localtv.settings
from localtv import models
from localtv import utils
import localtv.tiers

from vidscraper.errors import CantIdentifyUrl
from vidscraper import auto_feed


class BulkFormSetMixin(object):
    """
    Mixin form-like which adds a bulk field to each form.
    """
    def add_fields(self, form, i):
        super(BulkFormSetMixin, self).add_fields(form, i)
        if i < self.initial_form_count():
            form.fields['BULK'] = forms.BooleanField(required=False)

    @property
    def bulk_forms(self):
        for form in self.initial_forms:
            if (hasattr(form, 'cleaned_data') and
                form.cleaned_data.get('BULK') and
                not self._should_delete_form(form)):
                yield form

class BulkChecklistField(forms.ModelMultipleChoiceField):
    widget = forms.CheckboxSelectMultiple

    def label_from_instance(self, instance):
        if isinstance(instance, User):
            if instance.first_name:
                name = '%s %s' % (instance.first_name,
                                  instance.last_name)
            else:
                name = instance.username
        else:
            name = instance.name
        return mark_safe(u'<span>%s</span>' % (
                conditional_escape(name)))


class WidgetSettingsForm(forms.ModelForm):

    class Meta:
        model = models.WidgetSettings
        exclude = ['site', 'has_thumbnail', 'thumbnail_extension']

    def save(self):
        ws = forms.ModelForm.save(self)
        if ws.icon:
            ws.icon.open()
            cf = ContentFile(ws.icon.read())
            ws.save_thumbnail_from_file(cf)
        return ws
