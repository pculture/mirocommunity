# This file is part of Miro Community.
# Copyright (C) 2009, 2010 Participatory Culture Foundation
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

from django import forms
from django.utils.translation import ugettext_lazy as _

from django.conf import settings
from django.contrib.comments import forms as comment_forms

try:
    from recaptcha_django import ReCaptchaField
except ImportError:
    ReCaptchaField = None

class CommentForm(comment_forms.CommentForm):
    comment = forms.CharField(label=_("Comment"), widget=forms.Textarea,
                              max_length=comment_forms.COMMENT_MAX_LENGTH)
    email = forms.EmailField(label=_("Email address"),
                             required=False)
    if ReCaptchaField and not settings.DEBUG and \
            settings.RECAPTCHA_PRIVATE_KEY:
        captcha = ReCaptchaField()

    def __init__(self, target_object, data=None, initial=None):
        comment_forms.CommentForm.__init__(self, target_object, data, initial)
        if 'captcha' in self.fields and data and 'user' in data:
            from localtv.models import SiteLocation # avoid circular import
            if SiteLocation.objects.get_current().user_is_admin(data['user']):
                del self.fields['captcha']

