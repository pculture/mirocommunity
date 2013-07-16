from django.conf.urls.defaults import patterns
from django.views.generic.simple import direct_to_template


urlpatterns = patterns('',
    (r'^widget/$', direct_to_template, {
            'template': 'localtv/goodies/widget.html'},
     'localtv_goodies_widget')
)
