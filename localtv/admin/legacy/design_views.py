from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect

from localtv.admin.legacy import forms
from localtv.decorators import require_site_admin
from localtv.models import SiteSettings, WidgetSettings


@require_site_admin
@csrf_protect
def edit_settings(request, form_class=forms.EditSettingsForm):
    site_settings = SiteSettings.objects.get_current()
    form = form_class(instance=site_settings)

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES,
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
    if request.method == 'POST':
        form = forms.WidgetSettingsForm(
            request.POST,
            request.FILES,
            instance=WidgetSettings.objects.get_current())
        if form.is_valid():
            widgetsettings = form.save()
            if request.POST.get('delete_icon'):
                if widgetsettings.icon:
                    widgetsettings.icon.delete()
            if request.POST.get('delete_css'):
                if widgetsettings.css:
                    widgetsettings.css.delete()
            return HttpResponseRedirect(
                reverse('localtv_admin_widget_settings'))
    else:
        widgetsettings = WidgetSettings.objects.get_current()
        form = forms.WidgetSettingsForm(
            instance=widgetsettings,
            initial={
                'title': widgetsettings.get_title_or_reasonable_default()})

    return render_to_response(
        'localtv/admin/widget_settings.html',
        {'form': form},
        context_instance=RequestContext(request))
