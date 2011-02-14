# This file is part of Miro Community.
# Copyright (C) 2010, 2011 Participatory Culture Foundation
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

import logging
import datetime

from django.conf import settings
import django.contrib.auth.models
from django.core.mail import EmailMessage
from django.template import Context, loader

import localtv.models

import uploadtemplate.models

def nightly_warnings():
    '''This returns a dictionary, mapping English-language reasons to
    localtv.admin.tiers functions to call.'''
    sitelocation = localtv.models.SiteLocation.objects.get_current()
    current_tier = sitelocation.get_tier()
    ret = set()
    if should_send_video_allotment_warning(sitelocation, current_tier):
        ret.add('video_allotment_warning_sent')
    if should_send_five_day_free_trial_warning(sitelocation):
        ret.add('free_trial_warning_sent')
    if should_send_inactive_site_warning(sitelocation, current_tier):
        ret.add('inactive_site_warning_sent')
    return ret

def get_main_site_admin():
    superusers = django.contrib.auth.models.User.objects.filter(is_superuser=True)
    first_ones = superusers.order_by('pk')
    if first_ones:
        return first_ones[0]
    return None # eek, any callers had better check for this.

def should_send_inactive_site_warning(sitelocation, current_tier):
    # If we have already sent the warning, refuse to send it again.
    if sitelocation.inactive_site_warning_sent:
        return False

    # Grab the time the main site admin last logged in. If it is greater
    # than six weeks, then yup, the admin gets a warning.
    SIX_WEEKS = datetime.timedelta(days=7 * 6)
    main_site_admin = get_main_site_admin()
    if not main_site_admin:
        raise ValueError, "Uh, this site has no admin. Something has gone horribly wrong."
    if (datetime.datetime.utcnow() - main_site_admin.last_login) > SIX_WEEKS:
        return True

def should_send_video_allotment_warning(sitelocation, current_tier):
    # Check for the video warning having already been sent
    if sitelocation.video_allotment_warning_sent:
        return False

    if current_tier.remaining_videos_as_proportion() < (1/3.0):
        return True

def should_send_five_day_free_trial_warning(sitelocation):
    time_remaining = sitelocation.time_until_free_trial_expires()
    if time_remaining is None:
        return False
    if sitelocation.free_trial_warning_sent:
        return False
    if time_remaining <= datetime.timedelta(days=5):
        return True
    return False

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

    # If the site has a custom domain, and the future tier doesn't permit it, then
    # we should warn the user.
    if (sitelocation.enforce_tiers()
        and sitelocation.site.domain
        and not sitelocation.site.domain.endswith('mirocommunity.org')
        and not future_tier.permits_custom_domain()):
        warnings.add('customdomain')

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
        count = 0
    count = (current_count - new_limit)
    if not actually_do_it:
        return count

    if count <= 0:
        return

    disabled_this_many = 0
    disable_these_videos = current_videos_that_count_toward_limit().order_by('-pk')[:count]
    for vid in disable_these_videos:
        vid.status = localtv.models.VIDEO_STATUS_UNAPPROVED
        vid.save()
        disabled_this_many += 1
    return disabled_this_many

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
    __slots__ = ['tier_name', 'NAME_TO_COST']

    NAME_TO_COST = {'basic': 0,
                    'plus': 15,
                    'premium': 35,
                    'max': 75}

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

    def permits_custom_domain(self):
        special_cases = {'basic': False}
        return special_cases.get(self.tier_name, True)

    def videos_limit(self):
        special_cases = {'basic': 500,
                         'plus': 1000,
                         'premium': 5000,
                         'max': 25000}
        return special_cases[self.tier_name]

    def over_videos_limit(self):
        return (self.remaining_videos >= 0)

    def remaining_videos(self):
        return self.videos_limit() - current_videos_that_count_toward_limit().count()

    def remaining_videos_as_proportion(self):
        return (self.remaining_videos() * 1.0 / self.videos_limit())

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
        special_cases = self.NAME_TO_COST
        return special_cases[self.tier_name]

class PaymentException(Exception):
    pass

class WrongPaymentSecret(PaymentException):
    pass

class WrongAmount(PaymentException):
    pass

class WrongStartDate(PaymentException):
    pass

def process_payment(dollars, payment_secret, start_date):
    site_location = localtv.models.SiteLocation.objects.get_current()
    if payment_secret != site_location.payment_secret:
        raise WrongPaymentSecret()

    # Reverse the NAME_TO_COST dictionary to grab the name from
    # the cost.
    cost2name = dict(map(reversed, Tier.NAME_TO_COST.items()))
    if dollars in cost2name:
        target_tier_name = cost2name[dollars]
    else:
        raise WrongAmount()

    # Check the start_date. It should be within a day of right now
    # (if there is a free trial available, we push NOW forward
    # by 30 days)
    NOW = datetime.datetime.utcnow()
    if site_location.free_trial_available:
        NOW += datetime.timedelta(days=30)
    difference = NOW - start_date
    # If the delta is too large, raise WrongStartDate
    if abs(difference) > datetime.timedelta(days=1):
        pass # raise WrongStartDate()

    target_tier = Tier(target_tier_name)
                     
    amount_due = target_tier.dollar_cost()
    if (amount_due > 0) and (
        dollars == amount_due):
        site_location.payment_due_date = add_a_month(
            site_location.payment_due_date or
            NOW)
        site_location.free_trial_available = False
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
    ## FIXME: this has to be changed, based on the new handling of Paypal and free trials.
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

    current_tier_obj = Tier(current_tier_name)
    new_tier_obj= Tier(new_tier_name)

    if new_tier_obj.dollar_cost() > current_tier_obj.dollar_cost():
        # Send an email about the transition
        template_name = 'localtv/admin/tiers_emails/welcome_to_tier.txt'
        subject = '%s has been upgraded!' % (current_siteloc.site.name or current_siteloc.site.domain)

        # Pass in the new, modified sitelocation instance. That way, it has the new tier.
        send_tiers_related_email(subject, template_name, sitelocation=instance)

def pre_save_adjust_resource_usage(instance, signal, **kwargs):
    ### Check if tiers enforcement is disabled. If so, bail out now.
    if not localtv.models.SiteLocation.enforce_tiers():
        return

    # Check if there is an existing SiteLocation. If not, we should bail
    # out now.
    current_sitelocs = localtv.models.SiteLocation.objects.filter(site__pk=settings.SITE_ID)
    if not current_sitelocs:
        return
    # This dance defeats the SiteLocation cache.
    current_siteloc = current_sitelocs[0]

    # When transitioning between any two site tiers, make sure that
    # the number of admins there are on the site is within the tier.
    new_tier_name = instance.tier_name
    new_tier_obj = Tier(new_tier_name)
    push_number_of_admins_down(new_tier_obj.admins_limit(),
                               actually_demote_people=True)

    # When transitioning down from a tier that permitted custom domains,
    # and if the user had a custom domain, then this website should automatically
    # file a support request to have the site's custom domain disabled.
    if 'customdomain' in user_warnings_for_downgrade(new_tier_name):
        send_tiers_related_email(subject="Remove custom domain for %s" % instance.site.domain,
                                 template_name="localtv/admin/tiers_emails/disable_my_custom_domain.txt",
                                 sitelocation=instance,
                                 override_to=['support@mirocommunity.org'])

    # Push the published videos into something within the limit
    hide_videos_above_limit(new_tier_obj, actually_do_it=True)

    # Also change the theme, if necessary.
    switch_to_a_bundled_theme_if_necessary(new_tier_obj, actually_do_it=True)

def send_tiers_related_email(subject, template_name, sitelocation, override_to=None):
    # Send it to the site superuser with the lowest ID
    first_one = get_main_site_admin()
    if not first_one:
        logging.error("Hah, there is no site admin. Screw email.")
        return

    if not first_one.email:
        logging.error("Hah, there is a site admin, but that person has no email address set. Email is hopeless.")
        return

    if sitelocation.payment_due_date:
        next_payment_due_date = sitelocation.payment_due_date.strftime('%Y-%m-%d')
    else:
        next_payment_due_date = None

    # Generate the email
    t = loader.get_template(template_name)
    c = Context({'site': sitelocation.site,
                 'in_free_trial': sitelocation.in_free_trial,
                 'tier_obj': sitelocation.get_tier(),
                 'tier_name_capitalized': sitelocation.tier_name.title(),
                 'site_name': sitelocation.site.name or sitelocation.site.domain,
                 'video_count': current_videos_that_count_toward_limit().count(),
                 'short_name': first_one.first_name or first_one.username,
                 'next_payment_due_date': next_payment_due_date,
                 })
    message = t.render(c)

    recipient_list = [first_one.email]
    if override_to:
        assert type(override_to) in (list, tuple)
        recipient_list = override_to

    # Send the sucker
    from django.conf import settings
    EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL,
                 recipient_list).send(fail_silently=False)
