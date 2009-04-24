from django.conf.urls.defaults import patterns

from localtv.openid.views import redirect_to_login_or_register

urlpatterns = patterns(
    '',
    (r'^$', 'django_openidconsumer.views.begin',
     {'sreg': 'email,nickname'}, 'localtv_openid_start'),
    (r'^complete/$', 'django_openidconsumer.views.complete',
     {'on_success': redirect_to_login_or_register}, 'localtv_openid_complete'),
    (r'^login_or_register/$', 'localtv.openid.views.login_or_register',
     {}, 'localtv_openid_login_or_register'),
    (r'^signout/$', 'localtv.openid.views.signout',
     {}, 'localtv_openid_signout'),
)

