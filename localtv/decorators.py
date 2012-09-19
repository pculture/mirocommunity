from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseRedirect


def request_passes_test(test_func):
    def decorate(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not test_func(request, *args, **kwargs):
                return redirect_to_login(request.get_full_path())
            else:
                return view_func(request, *args, **kwargs)

        return wrapper

    return decorate


require_site_admin = request_passes_test(
    lambda request, *a, **k: request.user_is_admin())


def referrer_redirect(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        if response.status_code != 200:
            return response # don't break other redirects
        requested_with = request.META.get('HTTP_X_REQUESTED_WITH')
        if requested_with == 'XMLHttpRequest':
            return response # don't do redirects for AJAX calls
        referer = request.META.get('HTTP_REFERER')
        if referer is not None:
            return HttpResponseRedirect(referer)
        else:
            return response

    return wrapper
