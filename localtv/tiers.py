import logging
from django.conf import settings
import localtv.models

## These "CHOICES" are used in the SiteLocation model.
## They describe the different account types.
CHOICES = [
    ('free', 'Free account'),
    ('plus', 'Plus account'),
    ('premium', 'Premium account'),
    ('executive', 'Executive account')]

class Tier(object):
    def __init__(self, tier_name):
        self.tier_name = tier_name

    @staticmethod
    def get(log_warnings=False):
        DEFAULT = None

        # Iterative sanity checks
        # We have a settings.SITE_ID, right?
        site_id = getattr(settings, 'SITE_ID', None)
        if site_id is None and log_warnings:
            logging.warn("Eek, SITE_ID is None.")
            return DEFAULT
        # We have a SiteLocation, right?
        try:
            sl = localtv.models.SiteLocation.objects.get(site=site_id)
        except localtv.models.SiteLocation.DoesNotExist:
            if log_warnings:
                logging.warn("Eek, SiteLocation does not exist.")
            return DEFAULT

        # We have a tier set, right?
        if sl.tier_name:
            # Good, then just call get_tier() and return the result.
            return sl.get_tier()
        else:
            if log_warnings:
                logging.warn("Eek, we have no tier set.")
            return DEFAULT

    def videos_limit(self):
        special_cases = {'free': 500,
                         'plus': 1000,
                         'premium': 5000,
                         'executive': 25000}
        return special_cases[self.tier_name]

    def admins_limit(self):
        special_cases = {'free': 1,
                         'plus': 5}
        default = None
        return special_cases.get(self.tier_name, default)

    def permit_custom_css(self):
        special_cases = {'free': False}
        default = True
        return special_cases.get(self.tier_name, default)

    def permit_custom_template(self):
        special_cases = {'executive': True}
        default = False
        return special_cases.get(self.tier_name, default)

    def dollar_cost(self):
        special_cases = {'free': 0,
                         'plus': 15,
                         'premium': 35,
                         'executive': 75}
        return special_cases[self.tier_name]

class BooleanRepresentingUploadTemplatePermission(object):
    def __nonzero__(self):
        default = False # By default, we say that custom themes are disabled.

        tier = Tier.get()
        if tier is None:
            return default
        return tier.permit_custom_css()
        
    def __init__(self):
        # Call Tier.get() and log any warnings that come up.
        # Throw away the result so that we can always check the tier
        # at the latest possible time.
        Tier.get(log_warnings=True)
