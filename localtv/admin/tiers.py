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

from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.utils.encoding import force_unicode
from django.views.decorators.csrf import csrf_protect
from django.core.urlresolvers import reverse

from localtv.decorators import require_site_admin
from localtv import models
from localtv.util import SortHeaders, MockQueryset
from localtv.admin import forms

import localtv.tiers

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
    # validate
    if target_tier_name in dict(localtv.tiers.CHOICES):
        # Would the user lose anything? If so, stop the process to warn the user.
        would_lose = localtv.tiers.user_warnings_for_downgrade(target_tier_name)
        if would_lose:
            return HttpResponseRedirect(reverse('localtv_admin_downgrade_confirm') + '?tier_name=' + target_tier_name)
        return confirmed_change_tier(request, override_tier=target_tier_name)
    else:
        return HttpResponseRedirect(reverse('localtv_admin_tier'))

@require_site_admin
@csrf_protect
def confirmed_change_tier(request, override_tier = None):
    if override_tier:
        target_tier_name = override_tier
    else:
        target_tier_name = request.POST.get('tier_name', '')
    # validate
    if target_tier_name in dict(localtv.tiers.CHOICES):
        target_tier_obj = localtv.tiers.Tier(target_tier_name)

        # Switch our tier
        sl = request.sitelocation
        sl.tier_name = target_tier_name
        sl.save()
        
        # The below code should cause a PayPal redirect. Instead, it simply emulates full
        # payment.
        localtv.tiers.process_payment(
            dollars=request.sitelocation.get_tier().dollar_cost(),
            payment_secret=request.sitelocation.payment_secret,
            start_date=datetime.datetime.utcnow())
                                      

    # Always redirect back to tiers page
    return HttpResponseRedirect(reverse('localtv_admin_tier'))

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
