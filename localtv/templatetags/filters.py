from django.template import Library

register = Library()

def simpletimesince(value, arg=None):
    """Formats a date as the time since that date (i.e. "4 days, 6 hours")."""
    from django.utils.timesince import timesince
    if not value:
        return u''
    try:
        if arg:
            return timesince(value, arg)
        return timesince(value).split(', ')[0]
    except (ValueError, TypeError):
        return u''
simpletimesince.is_safe = False

register.filter(simpletimesince)
