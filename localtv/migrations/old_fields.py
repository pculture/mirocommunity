"""
This module contains fields that are required for migrations, but which are no
longer used.
"""

from django.conf import settings
from django.db import models

try:
    import bitly
except ImportError:
    bitly = None

class BitLyWrappingURLField(models.URLField):

    def clean(self, value, video):
        if bitly is not None and getattr(settings, 'BITLY_LOGIN', None):
            # Workaround for some cases
            if value is None:
                value = ''
            if len(value) > self.max_length: # too long
                api = bitly.Api(login=settings.BITLY_LOGIN,
                                apikey=settings.BITLY_API_KEY)
                try:
                    value = unicode(api.shorten(value))
                except bitly.BitlyError:
                    pass
        return super(BitLyWrappingURLField, self).clean(value, video)


class Migration(object):
    """
    This is a HACK because South thinks of this file as a migration.  We don't
    do anything if it tries to run us.
    """
    def forwards(self):
        pass

    def backwards(self):
        pass
