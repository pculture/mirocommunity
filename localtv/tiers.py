import logging
import datetime

from django.conf import settings
import django.contrib.auth.models

import localtv.models

import uploadtemplate.models

def user_warnings_for_downgrade(new_tier_name):
    warnings = set()

    sitelocation = localtv.models.SiteLocation.objects.get_current()
    current_tier = sitelocation.get_tier()
    future_tier = Tier(new_tier_name)

    # How many admins do we have right now?
    current_admins_count = number_of_admins_including_superuser()
    # How many are we permitted to, in the future?
    future_admins_permitted = future_tier.admins_limit()

    if future_admins_permitted is not None:
        if current_admins_count > future_admins_permitted:
            warnings.add('admins')

    # Is there a custom theme? If so, check if we will have to ditch it.
    if (uploadtemplate.models.Theme.objects.filter(bundled=False) and
        current_tier.permit_custom_template()):
        # Does the future tier permit a custom theme? If not, complain:
        if not future_tier.permit_custom_template():
            warnings.add('customtheme')

    # If the old tier permitted advertising, and the new one does not,
    # then let the user know about that change.
    if (current_tier.permits_advertising() and 
        not future_tier.permits_advertising()):
        warnings.add('advertising')

    # If the old tier permitted custom CSS, and the new one does not,
    # and the site has custom CSS in use, then warn the user.
    if (current_tier.permit_custom_css() and
        not future_tier.permit_custom_css() and
        sitelocation.css.strip()):
            warnings.add('css')

    if current_videos_that_count_toward_limit().count() > future_tier.videos_limit():
        warnings.add('videos')

    return warnings

### XXX Merge all these functions into one tidy little thing.

def current_videos_that_count_toward_limit():
    return localtv.models.Video.objects.filter(status=localtv.models.VIDEO_STATUS_ACTIVE)

def hide_videos_above_limit(future_tier_obj, actually_do_it=False):
    new_limit = future_tier_obj.videos_limit()
    current_count = current_videos_that_count_toward_limit().count()
    if current_count <= new_limit:
        return 0
    return (current_count - new_limit)

def switch_to_a_bundled_theme_if_necessary(future_tier_obj, actually_do_it=False):
    if uploadtemplate.models.Theme.objects.filter(default=True):
        current_theme = uploadtemplate.models.Theme.objects.get_default()
        if not current_theme.bundled:
            if not future_tier_obj.permit_custom_template():
                # Grab the bundled theme with the lowest ID, and make it the default.
                # If there is no such theme, log an error, but do not crash.
                bundleds = uploadtemplate.models.Theme.objects.filter(bundled=True).order_by('pk')
                if bundleds:
                    first = bundleds[0]
                    if actually_do_it:
                        first.set_as_default()
                    return first.name
                else:
                    logging.error("Hah, there are no bundled themes left.")
                    return None

def push_number_of_admins_down(new_limit, actually_demote_people=False):
    '''Return a list of usernames that will be demoted.

    If you pass actually_demote_people in as True, then the function will actually
    remove people from the admins set.'''
    # None is the special value indicating there is no limit.
    if new_limit is None:
        return

    # No matter what, the super-user is going to still be an admin.
    # Therefore, any limit has to be greater than or equal to one.
    assert new_limit >= 1

    # grab hold of the current SiteLocation
    try:
        sitelocation = localtv.models.SiteLocation.objects.get_current()
    except localtv.models.SiteLocation.DoesNotExist, e:
        return # well okay, there is no current SiteLocation.

    # We have this many right now
    initial_admins_count = number_of_admins_including_superuser()

    # If we do not have excess admins, we can quit early.
    demote_this_many = initial_admins_count - new_limit
    if demote_this_many <= 0:
        return

    # Okay, we have to actually demote some users from admin.
    # Well, uh, sort them by user ID.
    demotees = sitelocation.admins.order_by('-pk')[:demote_this_many]
    demotee_usernames = set([x.username for x in demotees])
    if actually_demote_people:
        for demotee in demotees:
            sitelocation.admins.remove(demotee)
    return demotee_usernames
    

def number_of_admins_including_superuser():
    if not localtv.models.SiteLocation.objects.all():
        return 0

    normal_admin_ids = set([k.id for k in
                            localtv.models.SiteLocation.objects.get_current().admins.filter(is_active=True)])
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
    ('max', 'Max account')]

class Tier(object):
    __slots__ = ['tier_name']

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

    def permits_advertising(self):
        special_cases = {'premium': True,
                         'max': True}
        return special_cases.get(self.tier_name, False)

    def videos_limit(self):
        special_cases = {'basic': 500,
                         'plus': 1000,
                         'premium': 5000,
                         'max': 25000}
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
        special_cases = {'max': True}
        default = False
        return special_cases.get(self.tier_name, default)

    def dollar_cost(self):
        special_cases = {'basic': 0,
                         'plus': 15,
                         'premium': 35,
                         'max': 75}
        return special_cases[self.tier_name]

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

def pre_save_adjust_resource_usage(instance, signal, **kwargs):
    # When tranisitioning between any two site tiers, make sure that
    # the number of admins there are on the site is within the tier.
    new_tier_name = instance.tier_name
    new_tier_obj = Tier(new_tier_name)
    push_number_of_admins_down(new_tier_obj.admins_limit(),
                               actually_demote_people=True)

    # Also change the theme, if necessary.
    switch_to_a_bundled_theme_if_necessary(new_tier_obj, actually_do_it=True)
    
