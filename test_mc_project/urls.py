from django.conf.urls.defaults import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = (
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) +
    static(settings.UPLOADTEMPLATE_MEDIA_URL,
           document_root=settings.UPLOADTEMPLATE_MEDIA_ROOT) +
    patterns('',
        url(r'^', include('localtv.contrib.contests.urls')),
        url(r'^', include('localtv.urls')),
    )
)
