# Copyright 2009 - Participatory Culture Foundation
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

from django import forms
from django.contrib.auth import models

class OpenIdRegistrationForm(forms.Form):
    # we don't really need the openid url since that's in the session..
    email = forms.EmailField()
    nickname = forms.CharField(max_length=30)

    def clean_nickname(self):
        value = self.cleaned_data.get('nickname', '')
        if not value:
            return value

        if models.User.objects.filter(username=value).count() > 0:
            raise forms.ValidationError('Nickname "%s" already exists; please '
                                        'choose again.' % value)
        return value

