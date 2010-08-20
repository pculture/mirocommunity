from django.conf.urls.defaults import patterns, include

urlpatterns = patterns('',
                       (r'^(?P<path>(?:css|images|js|swf|versioned).*)', 'django.views.static.serve',
                        {'document_root': '../src/miro-community/static/'}),
                       (r'^localtv/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'localtv'}),
                       (r'^uploadtemplate/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'uploadtemplate'}),
                       #(r'^openid/', include('localtv_openid.urls')),
                       (r'', include('localtv.urls')),
                       )

