# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
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
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.template.defaultfilters import pluralize
from django.utils.translation import ugettext_lazy as _

from localtv.models import SiteLocation
from localtv.tiers import Tier, number_of_admins_including_superuser
from localtv.utils import get_profile_model


Profile = get_profile_model()


class BaseProfileForm(forms.ModelForm):
    first_name_field = User._meta.get_field('first_name')
    last_name_field = User._meta.get_field('last_name')
    username_field = User._meta.get_field('username')

    first_name = first_name_field.formfield(required=False)
    last_name = last_name_field.formfield(required=False)
    username = username_field.formfield()

    password1 = forms.CharField(label=_("Password"), required=False,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password (again)"), required=False,
                                widget=forms.PasswordInput)

    class Meta:
        model = Profile
        exclude = ['user']

    def __init__(self, *args, **kwargs):
        super(BaseProfileForm, self).__init__(*args, **kwargs)
        if self.instance.user_id:
            self.user = self.instance.user
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['username'].initial = self.user.username
        else:
            self.user = User()

    def clean_first_name(self):
        return self.first_name_field.clean(self.cleaned_data['first_name'],
                                           self.user)

    def clean_last_name(self):
        return self.last_name_field.clean(self.cleaned_data['last_name'],
                                          self.user)

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return self.username_field.clean(self.cleaned_data['username'],
                                             self.user)
        raise ValidationError(_("A user with that username already exists."))
        

    def clean(self):
        cleaned_data = super(BaseProfileForm, self).clean()
        if cleaned_data['password1'] != cleaned_data['password2']:
            raise ValidationError(_("The two password fields didn't match."))
        return cleaned_data

    def save_user(self, commit=True):
        password = self.cleaned_data['password1']
        if password:
            self.user.set_password(password)
        self.user.username = self.cleaned_data['username']

        # first_name and last_name may be removed by a subclass
        self.user.first_name = self.cleaned_data.get('first_name', '')
        self.user.last_name = self.cleaned_data.get('last_name', '')

        if commit:
            self.user.save()
        return self.user

    def save(self, commit=True):
        # Only save the user if the result is being committed.
        if commit:
            self.save_user()
            self.instance.user = self.user
        return super(BaseProfileForm, self).save(commit)



class UserProfileForm(BaseProfileForm):
    """Form for a user to edit their own profile."""
    old_password = forms.CharField(label=_("Old password"),
                                   widget=forms.PasswordInput,
                                   help_text="Required to change your password "
                                             "or username.")
    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['password1'].label = _("New password")
        self.fields['password2'].label = _("New password confirmation")

    def clean_old_password(self):
        old_password = self.cleaned_data["old_password"]
        if not self.user.check_password(old_password):
            raise ValidationError(_("Your old password was entered incorrectly."
                                    " Please enter it again."))
        return old_password


class AdminProfileForm(BaseProfileForm):
    """Form for an admin to edit a user's profile."""
    role = forms.ChoiceField(choices=(
            ('user', 'User'),
            ('admin', 'Admin')),
            widget=forms.RadioSelect,
            required=False, initial='user')

    def __init__(self, *args, **kwargs):
        super(AdminProfileForm, self).__init__(*args, **kwargs)
        self.sitelocation = SiteLocation.objects.get_current()
        if self.instance.user_id:
            if self.sitelocation.user_is_admin(self.instance.user):
                self.fields['role'].initial = 'admin'
        else:
            for field in ('first_name', 'last_name', 'logo', 'location',
                          'description', 'website'):
                del self.fields[field]
            self.fields['password1'].help_text = _("If you do not specify a "
                               "password, the user will not be able to log in.")
    
        ## Add a note to the 'role' help text indicating how many admins
        ## are permitted with this kind of account.
        tier = Tier.get()
        if tier.admins_limit() is not None:
            message = 'With a %s, you may have %d administrator%s.' % (
                self.sitelocation.get_tier_name_display(),
                tier.admins_limit(),
                pluralize(tier.admins_limit()))
            self.fields['role'].help_text = message

    def clean_role(self):
        role = self.cleaned_data['role']
        if SiteLocation.enforce_tiers():
            if not self._validate_role_with_tiers_enforcement(role):
                permitted_admins = Tier.get().admins_limit()
                raise ValidationError("You already have %d admin%s in your "
                                      "site. Upgrade to have access to more." % 
                                      (permitted_admins,
                                       pluralize(permitted_admins))
                                     )

        return role

    def _validate_role_with_tiers_enforcement(self, role):
        # If the user tried to create an admin, but the tier does not
        # permit creating another admin, raise an error.
        permitted_admins = Tier.get().admins_limit()

        # Some tiers permit an unbounded number of admins. Then, anything goes.
        if permitted_admins is None:
            return True

        # All non-admin values are permitted
        if role !='admin':
            return True

        # All role values are permitted if the user is already an admin
        if self.instance and self.sitelocation.user_is_admin(self.instance):
            return True

        # Okay, so now we know we are trying to make someone an admin in a
        # tier where admins are limited.
        #
        # The question becomes: is there room for one more?
        num_admins = number_of_admins_including_superuser()
        if (num_admins + 1) <= permitted_admins:
            return True

        # Otherwise, gotta say no.
        return False

    def save(self, commit=True):
        created = not self.instance.pk
        instance = super(AdminProfileForm, self).save(commit=False)

        user = self.save_user(commit=False)
        if created and not self.cleaned_data['password1']:
            user.set_unusable_password()

        if commit:
            user.save()
            instance.user = user

        old_save_m2m = self.save_m2m
        def save_m2m():
            old_save_m2m()

            if self.cleaned_data['role'] == 'admin':
                if not user.is_superuser:
                    self.sitelocation.admins.add(user)
            else:
                self.sitelocation.admins.remove(user)

        if commit:
            instance.save()
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return instance

#AdminProfileFormSet = modelformset_factory(Profile,
#                                     form=AdminProfileForm,
#                                     can_delete=True,
#                                     extra=0)#