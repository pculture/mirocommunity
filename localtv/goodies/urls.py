from django.conf.urls.defaults import patterns
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',
    (r'^$', direct_to_template, {
            'template': 'localtv/goodies/index.html'},
     'localtv_goodies'),
    (r'^widget/$', direct_to_template, {
            'template': 'localtv/goodies/widget.html'},
     'localtv_goodies_widget'),
    (r'^bookmarklet/$', direct_to_template, {
            'template': 'localtv/goodies/bookmarklet.html'},
     'localtv_goodies_bookmarklet'))

