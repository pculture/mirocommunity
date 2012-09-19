import datetime

from django.contrib.auth.models import User


TWO_MONTHS = datetime.timedelta(days=62)


def site_too_old():
    try:
        last_login = User.objects.order_by('-last_login').values_list(
                                           'last_login', flat=True)[0]
    except IndexError:
        # Always too old if there are no users.
        return True
    if last_login + TWO_MONTHS < datetime.datetime.now():
        return True
    else:
        return False
