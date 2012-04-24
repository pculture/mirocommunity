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

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.views.decorators.csrf import csrf_protect

from localtv.admin import forms
from localtv.decorators import require_site_admin
from localtv.models import SiteSettings, WidgetSettings, NewsletterSettings


@require_site_admin
@csrf_protect
def edit_settings(request):
    site_settings = SiteSettings.objects.get_current()
    form = forms.EditSettingsForm(instance=site_settings)

    if request.method == 'POST':
        form = forms.EditSettingsForm(request.POST, request.FILES,
                                      instance=site_settings)
        if form.is_valid():
            site_settings = form.save()
            if request.POST.get('delete_background'):
                if site_settings.background:
                    site_settings.background.delete()
            return HttpResponseRedirect(
                reverse('localtv_admin_settings'))

    return render_to_response(
        "localtv/admin/edit_settings.html",
        {'form': form},
        context_instance=RequestContext(request))


@require_site_admin
@csrf_protect
def widget_settings(request):
    site_settings = SiteSettings.objects.get_current()
    form = forms.WidgetSettingsForm(
        instance=site_settings.site.widgetsettings,
        initial={'title': 
                 WidgetSettings.objects.get().get_title_or_reasonable_default()})

    if request.method == 'POST':
        form = forms.WidgetSettingsForm(
            request.POST,
            request.FILES,
            instance=site_settings.site.widgetsettings)
        if form.is_valid():
            widgetsettings = form.save()
            if request.POST.get('delete_icon'):
                if widgetsettings.icon:
                    widgetsettings.icon.delete()
                    widgetsettings.delete_thumbnail()
            if request.POST.get('delete_css'):
                if widgetsettings.css:
                    widgetsettings.css.delete()
            return HttpResponseRedirect(
                reverse('localtv_admin_widget_settings'))
    return render_to_response(
        'localtv/admin/widget_settings.html',
        {'form': form},
        context_instance=RequestContext(request))


@require_site_admin
@csrf_protect
def newsletter_settings(request):
    newsletter = NewsletterSettings.objects.get_current()

    form = forms.NewsletterSettingsForm(instance=newsletter)

    if request.method == 'POST':
        form = forms.NewsletterSettingsForm(request.POST, instance=newsletter)
        if form.is_valid():
            newsletter = form.save()
            if request.POST.get('send_email'):
                newsletter.send()
            elif request.POST.get('preview'):
                return HttpResponseRedirect(
                    reverse('localtv_newsletter'))
            return HttpResponseRedirect(
                reverse('localtv_admin_newsletter_settings'))

    return render_to_response(
        'localtv/admin/newsletter_settings.html',
        {'form': form},
        context_instance=RequestContext(request))

