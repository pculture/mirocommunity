from django.conf.urls.defaults import patterns

from localtv.views.openid import redirect_to_login_or_register

urlpatterns = patterns(
    '',
    (r'^openid/$', 'django_openidconsumer.views.begin',
     {'sreg': 'email,nickname'}, 'localtv_openid_start'),
    (r'^openid/complete/$', 'django_openidconsumer.views.complete',
     {'on_success': redirect_to_login_or_register}, 'localtv_openid_complete'),
    (r'^openid/login_or_register/$', 'localtv.views.openid.login_or_register',
     {}, 'localtv_openid_login_or_register'),
    (r'^openid/signout/$', 'django_openidconsumer.views.signout'),
)

