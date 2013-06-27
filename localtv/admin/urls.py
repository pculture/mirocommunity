from django.conf.urls import patterns, url, include

from localtv.admin.views import ModerationView
from localtv.decorators import require_site_admin as admin_view

urlpatterns = patterns('',
    url(r'^$', admin_view(ModerationView.as_view())),

    url(r'^', include('localtv.admin.legacy.urls')),
)
