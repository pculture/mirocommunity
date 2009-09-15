from django.conf import settings
from django import template

register = template.Library()


@register.simple_tag
def versioned(static_path):
    if not getattr(settings, 'USE_VERSION', None):
        return static_path
    else:
        return '/versioned/%s%s' % (
            settings.USE_VERSION,
            static_path)
