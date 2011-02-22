# Copyright 2010 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
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

import re
import datetime
import urllib

from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage
from django.db.models import Q
from django.db import transaction
from django.http import Http404, HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.utils.encoding import force_unicode
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.core.urlresolvers import reverse
from django.conf import settings

import paypal.standard.ipn.views

from localtv.decorators import require_site_admin
from localtv import models
from localtv.util import SortHeaders, MockQueryset
from localtv.admin import forms

import localtv.tiers
import localtv.paypal_snippet

@csrf_exempt
def paypal_return(request):
    '''This view is where PayPal sends users to upon success. Some things to note:

    * PayPal sends us an "auth" parameter that we cannot validate.
    * This should be a POST so that cross-site scripting can't just upgrade people's sites.
    * This is not as secure as I would like.

    Suggested improvements:
    * The view that sends people to PayPal should store some state in the database
      that this view checks. It only permits an upgrade in that situation.
    * That could be the internal "payment_secret" to prevent CSRF.
    * A tricky site admin could still try POST the right data to this view, which would
      trigger the tier change.

    If you want to exploit a MC site and change its tier, and you can cause an admin
    with a cookie that's logged-in to visit pages you want, and you can get that admin
    to do a POST, you still have to POST a value for the "auth" key. Note that this is
    why we do a sanity-check of tier+payment status every night; we will catch funny
    business within a day or so.'''
    auth = request.POST.get('auth', None) or request.GET.get('auth', None)
    if not auth:
        return HttpResponseForbidden("You failed to submit an 'auth' token.")
    return HttpResponseRedirect(reverse('localtv_admin_tier'))

@require_site_admin
@csrf_protect
def upgrade(request):
    SWITCH_TO = 'Switch to this'
    UPGRADE = 'Upgrade Your Account'

    switch_messages = {}
    if request.sitelocation.tier_name in ('premium', 'max'):
        switch_messages['plus'] = SWITCH_TO
    else:
        switch_messages['plus'] = UPGRADE

    if request.sitelocation.tier_name == 'max':
        switch_messages['premium'] = SWITCH_TO
    else:
        switch_messages['premium'] = UPGRADE

    # Would you lose anything?
    would_lose = {}
    for tier_name in ['basic', 'plus', 'premium', 'max']:
        if tier_name == request.sitelocation.tier_name:
            would_lose[tier_name] = False
        else:
            would_lose[tier_name] = localtv.tiers.user_warnings_for_downgrade(tier_name)

    data = {}
    data['site_location'] = request.sitelocation
    data['would_lose_for_tier'] = would_lose
    data['switch_messages'] = switch_messages
    data['payment_secret'] = request.tier_info.get_payment_secret()
    data['offer_free_trial'] = request.tier_info.free_trial_available
    data['skip_paypal'] = getattr(settings, 'LOCALTV_SKIP_PAYPAL', False)
    if not data['skip_paypal']:
        p = localtv.paypal_snippet.PayPal.get_with_django_settings()
        data['paypal_url'] = p.PAYPAL_URL

    return render_to_response('localtv/admin/upgrade.html', data,
                              context_instance=RequestContext(request))

def user_is_okay_with_payment_so_we_can_really_switch_tier(request):
    '''The way this view works is that it does *not* require admin privileges.

    This is an unprivileged GET that can change HUGE things in the site, so it's really
    important that we keep it safe.

    For that reason, it only does the following things:

    * Looks up the target tier in the SiteLocation.payment_secret, which is a field that stores validated
      input from the admin site as to what tier the site wants to transition into.

    * It validates the token that PayPal passes to us. If the token is valid, it completes the tier transition process.

    Therefore, it is not valid to call this function if the tier does not cost money.'''
    target_tier_name = request.sitelocation.payment_secret
    target_tier_obj = localtv.tiers.Tier(target_tier_name)
    needs_valid_token = bool(target_tier_obj.dollar_cost())
    assert needs_valid_token
    
    # Create the recurring payment first.
    amount = target_tier_obj.dollar_cost()
    startdate = datetime.datetime.utcnow()
    # If there is a free trial permitted, push the start date of the recurring payment
    # forward by a month, and mark the free trial as used.
    used_free_trial = False
    if request.sitelocation.free_trial_available:
        startdate = localtv.tiers.add_a_month(startdate)
        request.sitelocation.free_trial_available = False
        request.sitelocation.payment_secret = ''
        request.sitelocation.save()
    success = _create_recurring_payment(request, request.GET.get('token', ''), amount, startdate)
    # FIXME: Look at the return code at some point.
    return _actually_switch_tier(request, target_tier_name)

def _create_recurring_payment(request, token, amount, startdate):
    p = localtv.paypal_snippet.PayPal(
        settings.PAYPAL_WPP_USER,
        settings.PAYPAL_WPP_PASSWORD,
        settings.PAYPAL_WPP_SIGNATURE)
    result = p.CreateRecurringPaymentsProfile(
        token, startdate=startdate.isoformat(),
        desc='Miro Community subscription',
        period='Month',
        freq='1',
        amt='%d.00' % amount)
    success = (result.get('PROFILESTATUS', [''])[0].lower() == 'activeprofile' and
               result.get('ACK', [''])[0].lower() == 'success')
    if success:
        request.sitelocation.current_paypal_profile_id = result.get('PROFILEID')[0]
        request.sitelocation.payment_due_date = startdate
        request.sitelocation.save()
        request.tier_info.user_has_successfully_performed_a_paypal_transaction = True
        request.tier_info.save()
    else:
        raise ValueError, "Um, that sucked. PayPal broke on us. FIXME."

def get_monthly_amount_of_paypal_subscription(subscription_id):
    # FIXME: Get this covered with a test.
    ti = localtv.models.TierInfo.objects.get_current()
    signups = paypal.standard.ipn.models.PayPalIPN.objects.filter(
        subscr_id=ti.current_paypal_profile_id, flag=False, txn_type='subscr_signup')
    if signups:
        signup = signups.order_by('-pk')[0]
        amount = float(signup.amount3)
        return amount
    raise ValueError, "Um, there is no current profile ID."

def downgrade_paypal_monthly_subscription(tier_info, target_amount):
    # FIXME: If the target amount is zero, cancel it
    return True # FIXME: Implement with PayPal NVP API

def _actually_switch_tier(request, target_tier_name):
    # Is there a monthly payment going on? If so, we should make sure its amount
    # is appropriate.
    target_tier_obj = localtv.tiers.Tier(target_tier_name)

    if getattr(settings, "LOCALTV_SKIP_PAYPAL", False):
        pass
    else:
        if False:
            target_amount = target_tier_obj.dollar_cost()
            
            current_amount = get_monthly_amount_of_paypal_subscription(request.tier_info.current_paypal_profile_id)

            if target_amount > current_amount:
                # Eek -- in this case, we cannot proceed.
                raise ValueError, "The existing PayPal ID needs to be upgraded."

            if target_amount < current_amount:
                downgrade_paypal_monthly_subscription(request.tier_info, target_amount)

    # Okay, the money downgrade worked. Thank heavens.
    #
    # Now it's safe to proceed with the internal tier switch.
    sl = request.sitelocation
    sl.tier_name = target_tier_name
    sl.save()

    # Always redirect back to tiers page
    return HttpResponseRedirect(reverse('localtv_admin_tier'))

@require_site_admin
@csrf_protect
def confirmed_change_tier(request, override_tier = None):
    if override_tier:
        target_tier_name = override_tier
    else:
        target_tier_name = request.POST.get('tier_name', '')
    # validate
    if target_tier_name not in dict(localtv.tiers.CHOICES):
        # Always redirect back to tiers page
        return HttpResponseRedirect(reverse('localtv_admin_tier'))

    target_tier_obj = localtv.tiers.Tier(target_tier_name)
    
    # Does this tier require payment? If not, we can just jump straight into it.
    # Note that this does not change anything about the free trial status. That's okay.
    use_paypal = True
    if not target_tier_obj.dollar_cost():
        use_paypal = False

    if getattr(settings, "LOCALTV_SKIP_PAYPAL", None):
        use_paypal = False

    if use_paypal:
        # Normally, the user has to permit us to charge them, first.
        return _generate_paypal_redirect(request, target_tier_name)
    else:
        # Sometimes we skip that step.
        return _actually_switch_tier(request, target_tier_name)

def _generate_paypal_redirect(request, target_tier_name):
    target_tier_obj = localtv.tiers.Tier(target_tier_name)
    assert target_tier_obj.dollar_cost() > 0

    # The sitelocation.payment_secret is where we store the PayPal token
    # that we temporarily use during this PayPal redirect process.
    #
    # It is only valid for three hours (according to PayPal), and moreover, it's
    # not really supposed to be kept a secret (since e.g. PayPal lets us pass it
    # over HTTP).

    # Assumption: The user has no current recurring transaction with us through PayPal.
    # We need to create one. To do this, we have to get authorization from PayPal.

    # The way that works is that the user has to go to PayPal to tell PayPal
    # that the user is okay with us drawing money from their account.
    #
    # We create a PayPal URL here for the user to go to. There, the user agrees to the
    # generic idea that we could do that.
    #
    # Once the user comes back, we actually create the recurring payment. That's handled
    # by user_is_okay_with_payment_so_we_can_really_switch_tier().
    p = localtv.paypal_snippet.PayPal(
        settings.PAYPAL_WPP_USER,
        settings.PAYPAL_WPP_PASSWORD,
        settings.PAYPAL_WPP_SIGNATURE)
    token = p.SetExpressCheckout(
        amount=0,
        return_url=request.build_absolute_uri(reverse(user_is_okay_with_payment_so_we_can_really_switch_tier)),
        cancel_url=request.build_absolute_uri(reverse(upgrade)),
        L_BILLINGTYPE0='RecurringPayments',
        L_BILLINGAGREEMENTDESCRIPTION0='Miro Community subscription',
        MAXAMT=target_tier_obj.dollar_cost())
    request.sitelocation.payment_secret = target_tier_name
    request.sitelocation.save()

    url = p.PAYPAL_URL + urllib.quote(token)
    return HttpResponseRedirect(url)

@require_site_admin
def downgrade_confirm(request):
    target_tier_name = request.GET.get('tier_name', '')
    if not target_tier_name:
        target_tier_name = request.POST.get('target_tier_name', None)
    # validate
    if target_tier_name in dict(localtv.tiers.CHOICES):
        target_tier_obj = localtv.tiers.Tier(target_tier_name)

        would_lose = localtv.tiers.user_warnings_for_downgrade(target_tier_name)
        if would_lose:
            data = {}
            data['tier_name'] = target_tier_name
            data['paypal_sandbox'] = getattr(settings, 'PAYPAL_TEST', False)
            p = localtv.paypal_snippet.PayPal.get_with_django_settings()
            data['paypal_url'] = p.PAYPAL_URL
            data['paypal_email'] = getattr(settings, 'PAYPAL_RECEIVER_EMAIL', '')
            data['target_tier_obj'] = target_tier_obj
            data['would_lose_admin_usernames'] = localtv.tiers.push_number_of_admins_down(target_tier_obj.admins_limit())
            data['customtheme_nag'] = ('customtheme' in would_lose)
            data['advertising_nag'] = ('advertising' in would_lose)
            data['customdomain_nag'] = ('customdomain' in would_lose)
            data['css_nag'] = ('css' in would_lose)
            data['videos_nag'] = ('videos' in would_lose)
            data['videos_over_limit'] = localtv.tiers.hide_videos_above_limit(target_tier_obj)
            data['new_theme_name'] = localtv.tiers.switch_to_a_bundled_theme_if_necessary(target_tier_obj)
            data['payment_secret'] = request.tier_info.get_payment_secret()
            return render_to_response('localtv/admin/downgrade_confirm.html', data,
                                      context_instance=RequestContext(request))
        else:
            # Okay! You clicked it. You're getting a real downgrade.
            return _actually_switch_tier(target_tier_name)
            
    # In some weird error case, redirect back to tiers page
    return HttpResponseRedirect(reverse('localtv_admin_tier'))

@csrf_exempt
def ipn_endpoint(request, payment_secret):
    # PayPal sends data to this function via POST.
    #
    # At this point in processing, the data might be fake. Let's pass it to
    # the django-paypal code and ask it to verify it for us.
    if payment_secret == request.tier_info.payment_secret:
        response = paypal.standard.ipn.views.ipn(request)
        return response
    return HttpResponseForbidden("You submitted something invalid to this IPN handler.")

from paypal.standard.ipn.signals import subscription_signup, subscription_cancel, subscription_eot, subscription_modify
def handle_recurring_profile_start(sender, **kwargs):
    ipn_obj = sender

    # If the thing is invalid, do not process any further.
    if ipn_obj.flag:
        return

    tier_info = localtv.models.TierInfo.objects.get_current()
    tier_info.current_paypal_profile_id = ipn_obj.subscr_id
    tier_info.save()

    # If we get the IPN, and we have not yet adjusted the tier name
    # to be at that level, now is a *good* time to do so.
    amount = float(ipn_obj.amount3)
    sitelocation = localtv.models.SiteLocation.objects.get_current()
    if sitelocation.get_tier().dollar_cost() == amount:
        pass
    else:
        # Find the right tier to move to
        tier_name = localtv.tiers.Tier.get_by_cost(amount)
        sitelocation.tier_name = tier_name
        sitelocation.save()

subscription_signup.connect(handle_recurring_profile_start)

def on_subscription_cancel_switch_to_basic(sender, **kwargs):
    ipn_obj = sender

    # If the thing is invalid, do not process any further.
    if ipn_obj.flag:
        return

    sitelocation = localtv.models.SiteLocation.objects.get_current()
    sitelocation.tier_name = 'basic'
    sitelocation.save()

    # Delete the current paypal subscription ID
    tier_info = localtv.models.TierInfo.objects.get_current()
    tier_info.current_paypal_profile_id = ''
    tier_info.payment_due_date = None
    tier_info.save()
subscription_cancel.connect(on_subscription_cancel_switch_to_basic)
subscription_eot.connect(on_subscription_cancel_switch_to_basic)
subscription_modify.connect(handle_recurring_profile_start)

@csrf_exempt
@require_site_admin
def begin_free_trial(request, payment_secret):
    '''This is where PayPal sends the user, if they are going to begin a free trial.

    At this stage, we do not know what tier the user wanted to opt into. That should be stored
    in the ?target_tier_name=... GET parameter.

    If it is some nonsense, we should show an obscure error message and tell them to email
    questions@MC if they got it.

    If it what we expect, then:

    * For now, trust that the IPN process will happen in the background,

    * Declare the free trial in-use, and

    * Switch the tier.'''
    if payment_secret != request.tier_info.payment_secret:
        raise HttpResponseForbidden("You are accessing this URL with invalid parameters. If you think you are seeing this message in error, email questions@mirocommunity.org")
    target_tier_name = request.GET.get('target_tier_name', '')
    if target_tier_name not in dict(localtv.tiers.CHOICES):
        return HttpResponse("Something went wrong switching your site level. Please send an email to questions@mirocommunity.org immediately.")

    # This is so that we can detect sites that start a free trial, but never generate
    # the IPN event.
    if request.tier_info.free_trial_started_on is None:
        request.tier_info.free_trial_started_on = datetime.datetime.utcnow()

    # Set the free trial to be in-use.
    if request.tier_info.free_trial_available:
        request.tier_info.free_trial_available = False
        request.tier_info.save()

    # Switch the tier!
    return _actually_switch_tier(request, target_tier_name)
