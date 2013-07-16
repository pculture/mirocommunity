from djam.riffs.admin import AdminRiff
from django.conf.urls import patterns, url, include


class MirocommunityAdminRiff(AdminRiff):
    def has_permission(self, request):
        return (request.user.is_active and request.user.is_authenticated and
                request.user_is_admin())

    def get_default_url(self):
        return self['localtv_video'].get_default_url()


admin_riff = MirocommunityAdminRiff()
admin_riff.autodiscover(with_modeladmins=False, with_batteries=False)


urlpatterns = patterns('',
    url(r'^', include(admin_riff.urls)),
)
