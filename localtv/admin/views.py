from djam.views.generic import UpdateView, FormView, RiffViewMixin
from django.http import Http404

from localtv.models import SiteSettings
from localtv.views import SubmitView


class ProfileView(UpdateView):
    def get_success_url(self):
        return self.request.path

    def get_object(self):
        if not self.request.user.is_authenticated():
            raise Http404
        return self.request.user


class NotificationsView(FormView):
    def get_success_url(self):
        return self.request.path

    def get_form_kwargs(self):
        if not self.request.user.is_authenticated():
            raise Http404
        kwargs = super(NotificationsView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return super(NotificationsView, self).form_valid(form)


class SettingsView(UpdateView):
    fieldsets = (
        (None, {
            'fields': ('name', 'logo', 'logo_contains_site_name',
                       'site_description')
        }),
        ('Customize design', {
            'fields': ('background', 'css', 'footer_content')
        }),
        ('Google analytics', {
            'fields': ('google_analytics_ua', 'google_analytics_domain')
        }),
        ('Social media', {
            'fields': ('facebook_admins',)
        }),
        ('Video Submission', {
            'fields': ('submission_allowed', 'submission_requires_login',
                       'submission_requires_email'),
        })
    )

    def get_success_url(self):
        return self.request.path

    def get_object(self):
        if not self.request.user_is_admin():
            raise Http404
        return SiteSettings.objects.get_current()


class VideoCreateView(RiffViewMixin, SubmitView):
    def get_success_url(self):
        return self.riff.reverse('update', kwargs={'pk': self.object.pk})
