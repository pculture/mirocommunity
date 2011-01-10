import logging
import datetime
from django.conf import settings
import localtv.models

def number_of_admins_including_superuser():
    normal_admin_ids = set([k.id for k in
                            localtv.models.SiteLocation.objects.get_current().admins.all()])
    super_user_ids = set(
        [k.id for k in
         django.contrib.auth.models.User.objects.filter(
                is_superuser=True)])
    normal_admin_ids.update(super_user_ids)
    num_admins = len(normal_admin_ids)
    return num_admins

## These "CHOICES" are used in the SiteLocation model.
## They describe the different account types.
CHOICES = [
    ('basic', 'Free account'),
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
        special_cases = {'basic': 500,
                         'plus': 1000,
                         'premium': 5000,
                         'executive': 25000}
        return special_cases[self.tier_name]

    def admins_limit(self):
        special_cases = {'basic': 1,
                         'plus': 5}
        default = None
        return special_cases.get(self.tier_name, default)

    def permit_custom_css(self):
        special_cases = {'basic': False}
        default = True
        return special_cases.get(self.tier_name, default)

    def permit_custom_template(self):
        special_cases = {'executive': True}
        default = False
        return special_cases.get(self.tier_name, default)

    def dollar_cost(self):
        special_cases = {'basic': 0,
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

def process_payment(dollars):
    site_location = localtv.models.SiteLocation.objects.get_current()
    amount_due = site_location.get_tier().dollar_cost()
    if dollars == amount_due:
        site_location.payment_due_date = add_a_month(site_location.payment_due_date)
        site_location.save()
    else:
        logging.error("Weird, the user paid %f but owed %f" % (
            dollars, amount_due))


def add_a_month(date):
    month = date.month
    new_date = None
    if 1 < month < 11:
        new_date = date.replace(month=month+1)
    else:
        new_date = date.replace(month=1, year=date.year+1)
    return new_date

### Here, we listen for changes in the SiteLocation
### As it changes, we make sure we adjust the payment due date stored in the SiteLocation.
def pre_save_set_payment_due_date(instance, signal, **kwargs):
    # If transitioning from 'basic' tier to something else,
    # set the payment_due_date to be now plus thirty days.

    # Right here, we do a direct filter() call to evade the SiteLocation cache.
    current_sitelocs = localtv.models.SiteLocation.objects.filter(site__pk=settings.SITE_ID)
    if not current_sitelocs:
        return

    current_siteloc = current_sitelocs[0]
    current_tier_name = current_siteloc.tier_name
    new_tier_name = instance.tier_name
    if (current_tier_name == 'basic') and (new_tier_name != 'basic'):
        # There should be no due date, because we used to be in 'basic' mode. If there was,
        # log an error.
        if instance.payment_due_date:
            logging.error("Yikes, there should have been no due date in free mode. But there was. Creepy.")
        # If the user can use a free trial, then the due date is a month from now
        if not current_siteloc.free_trial_available:
            
            instance.payment_due_date = datetime.datetime.utcnow()
        else:
            instance.payment_due_date = add_a_month(datetime.datetime.utcnow())
        

