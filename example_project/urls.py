from django.conf.urls.defaults import patterns, include

def get_localtv_path(sub_path):
    import os
    import localtv
    base = os.path.abspath(os.path.join(os.path.dirname(localtv.__file__), '..'))
    return os.path.join(base, sub_path)

urlpatterns = patterns('',
                       (r'^(?P<path>(?:css|images|js|swf|versioned).*)', 'django.views.static.serve',
                        {'document_root': get_localtv_path('static')}),
                       (r'^localtv/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'localtv'}),
                       (r'^uploadtemplate/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'uploadtemplate'}),
                       #(r'^openid/', include('localtv_openid.urls')),
                       (r'', include('localtv.urls')),
                       )

