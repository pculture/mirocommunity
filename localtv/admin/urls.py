from djam.batteries import UserRiff
from djam.riffs.admin import AdminRiff
from djam.riffs.auth import AuthRiff
from django.conf.urls import patterns, url, include

from localtv.admin.riffs import (VideoRiff, FeedRiff, ProfileRiff,
                                 NotificationsRiff, SettingsRiff,
                                 CategoryRiff)


class MirocommunityAdminRiff(AdminRiff):
    def has_permission(self, request):
        return (request.user.is_active and request.user.is_authenticated and
                request.user_is_admin())

    def get_default_url(self):
        return self['localtv_video'].get_default_url()


admin_riff = MirocommunityAdminRiff()

for cls in (AuthRiff, VideoRiff, CategoryRiff, FeedRiff, UserRiff, SettingsRiff,
            ProfileRiff, NotificationsRiff):
    admin_riff.register(cls)

urlpatterns = patterns('',
    url(r'^', include(admin_riff.urls)),
)
