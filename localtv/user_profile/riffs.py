from djam.riffs.base import Riff
from django.conf.urls import patterns, url

from localtv.user_profile.forms import ProfileForm, NotificationsForm
from localtv.user_profile.views import ProfileView, NotificationsView


class ProfileRiff(Riff):
    display_name = "Profile"

    def get_extra_urls(self):
        return patterns('',
            url(r'^$',
                ProfileView.as_view(
                    form_class=ProfileForm,
                    template_name='djam/form.html',
                    **self.get_view_kwargs()),
                name='profile'),
        )

    def get_default_url(self):
        return self.reverse('profile')


class NotificationsRiff(Riff):
    display_name = "Notifications"

    def get_extra_urls(self):
        return patterns('',
            url(r'^$',
                NotificationsView.as_view(
                    form_class=NotificationsForm,
                    template_name='djam/form.html',
                    **self.get_view_kwargs()),
                name='notifications'),
        )

    def get_default_url(self):
        return self.reverse('notifications')


riffs = [ProfileRiff, NotificationsRiff]
