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
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.utils.encoding import force_unicode
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.core.urlresolvers import reverse
from django.conf import settings

from localtv.decorators import require_site_admin
from localtv import models
from localtv.util import SortHeaders, MockQueryset
from localtv.admin import forms

import localtv.tiers
import localtv.paypal_snippet

@require_site_admin
@csrf_protect
def upgrade(request):
    SWITCH_TO = 'Switch to this'
    UPGRADE = 'Upgrade Your Account'

    siteloc = models.SiteLocation.objects.get_current()
    switch_messages = {}
    if siteloc.tier_name in ('premium', 'max'):
        switch_messages['plus'] = SWITCH_TO
    else:
        switch_messages['plus'] = UPGRADE

    if siteloc.tier_name == 'max':
        switch_messages['premium'] = SWITCH_TO
    else:
        switch_messages['premium'] = UPGRADE

    data = {}
    data['site_location'] = siteloc
    data['switch_messages'] = switch_messages

    return render_to_response('localtv/admin/upgrade.html', data,
                              context_instance=RequestContext(request))

@require_site_admin
# FIXME: Needs csrf protect; but that means that the preceding page has to be a form.
def change_tier(request):
    target_tier_name = request.GET.get('tier_name', '')
    # validation
    # First, is this a valid tier name? If not, just send the user right back to the upgrade page.
    if target_tier_name not in dict(localtv.tiers.CHOICES):
        return HttpResponseRedirect(reverse('localtv_admin_tier'))

    # If the user would lose features through this downgrade, then give the
    # user a chance to stop the transition.
    would_lose = localtv.tiers.user_warnings_for_downgrade(target_tier_name)
    if would_lose:
        return HttpResponseRedirect(reverse('localtv_admin_downgrade_confirm') + '?tier_name=' + target_tier_name)

    # Otherwise, let it be handled by the following view.
    return confirmed_change_tier(request, override_tier=target_tier_name)

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

def _actually_switch_tier(request, target_tier_name):
    ## Well, by this point, all payment validation has taken place. So we just
    ## switch the tier.
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

    # FIXME: Make sure PAYPAL_URL changes based on if we ar ein the sandbox or not
    url = p.PAYPAL_URL + urllib.quote(token)
    return HttpResponseRedirect(url)

@require_site_admin
def downgrade_confirm(request):
    target_tier_name = request.GET.get('tier_name', '')
    # validate
    if target_tier_name in dict(localtv.tiers.CHOICES):
        target_tier_obj = localtv.tiers.Tier(target_tier_name)

        would_lose = localtv.tiers.user_warnings_for_downgrade(target_tier_name)
        if would_lose:
            data = {}
            data['tier_name'] = target_tier_name
            data['target_tier_obj'] = target_tier_obj
            data['would_lose_admin_usernames'] = localtv.tiers.push_number_of_admins_down(target_tier_obj.admins_limit())
            data['customtheme_nag'] = ('customtheme' in would_lose)
            data['advertising_nag'] = ('advertising' in would_lose)
            data['customdomain_nag'] = ('customdomain' in would_lose)
            data['css_nag'] = ('css' in would_lose)
            data['videos_nag'] = ('videos' in would_lose)
            data['videos_over_limit'] = localtv.tiers.hide_videos_above_limit(target_tier_obj)
            data['new_theme_name'] = localtv.tiers.switch_to_a_bundled_theme_if_necessary(target_tier_obj)
            return render_to_response('localtv/admin/downgrade_confirm.html', data,
                                      context_instance=RequestContext(request))
        else:
            # Well, see, the point of this page is to show you what
            # you would lose.
            #
            # If you would lose nothing, you shouldn't even be here.
            # Sending you back to the tiers editing page...
            pass
            
    # Always redirect back to tiers page
    return HttpResponseRedirect(reverse('localtv_admin_tier'))
