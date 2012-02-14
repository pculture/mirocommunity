# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
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
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.template.defaultfilters import pluralize
from django.utils.translation import ugettext_lazy as _
from notification.models import (NoticeType, NoticeSetting, should_send,
                                 get_notification_setting)

from localtv.models import SiteLocation
from localtv.tiers import Tier, number_of_admins_including_superuser
from localtv.utils import get_profile_model

Profile = get_profile_model()


class BaseUserForm(forms.ModelForm):
    password1 = forms.CharField(label=_("New Password"), required=False,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("New Password (again)"), required=False,
                                widget=forms.PasswordInput)

    logo_field = Profile._meta.get_field('logo')
    location_field = Profile._meta.get_field('location')
    description_field = Profile._meta.get_field('description')
    website_field = Profile._meta.get_field('website')

    logo = logo_field.formfield()
    location = location_field.formfield()
    description = description_field.formfield()
    website = website_field.formfield()

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']

    def __init__(self, *args, **kwargs):
        super(BaseUserForm, self).__init__(*args, **kwargs)
        if self.instance.pk is not None:
            try:
                self.profile = self.instance.get_profile()
            except Profile.DoesNotExist:
                self.profile = Profile(user_id=self.instance.pk)
        else:
            self.profile = Profile()

        self.fields['logo'].initial = self.profile.logo
        self.fields['location'].initial = self.profile.location
        self.fields['description'].initial = self.profile.description
        self.fields['website'].initial = self.profile.website

    def clean_username(self):
        # This method is (strictly) unnecessary. We provide it to give a
        # friendlier error message.
        username = self.cleaned_data["username"]
        try:
            User.objects.exclude(pk=self.instance.pk).get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(_("A user with that username already exists."))

    def clean_password2(self):
        if self.cleaned_data['password1'] != self.cleaned_data['password2']:
            raise ValidationError(_("The two password fields didn't match."))
        return self.cleaned_data['password2']

    def _post_clean(self):
        super(BaseUserForm, self)._post_clean()
        # Admin form removes some fields if it's a user creation.
        self.profile.logo = self.cleaned_data.get('logo', '')
        self.profile.location = self.cleaned_data.get('location', '')
        self.profile.description = self.cleaned_data.get('description', '')
        self.profile.website = self.cleaned_data.get('website', '')
        try:
            self.profile.clean_fields(exclude=['user'])
        except ValidationError, e:
            self._update_errors(e.message_dict)

        try:
            self.profile.clean()
        except ValidationError, e:
            self._update_errors({NON_FIELD_ERRORS: e.messages})

    def save(self, commit=True):
        password = self.cleaned_data['password1']
        if password:
            self.instance.set_password(password)

        instance = super(BaseUserForm, self).save(commit=False)

        old_save_m2m = self.save_m2m
        def save_m2m():
            old_save_m2m()

            self.profile.user = instance
            self.profile.save()

        if commit:
            instance.save()
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return instance



class ProfileForm(BaseUserForm):
    """Form for a user to edit their own profile."""

    old_password = forms.CharField(required=False, label=_("Old password"),
                                   widget=forms.PasswordInput,
                                   help_text="Required to change your password,"
                                             " email, or username.")

    notifications = forms.MultipleChoiceField(required=False,
                                            choices=(),
                                            widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)

        sitelocation = SiteLocation.objects.get_current()
        user_is_admin = sitelocation.user_is_admin(self.instance)

        notification_field = self.fields['notifications']
        notice_types = NoticeType.objects.all()

        notification_choices = [
            (notice_type.pk, notice_type.description)
            for notice_type in notice_types
            if user_is_admin or not notice_type.label.startswith('admin_')
        ]
        notification_initial = [
            notice_type.pk for notice_type in notice_types
            if (user_is_admin or not notice_type.label.startswith('admin_')) and
            should_send(self.instance, notice_type, "1") 
        ]
        notification_field.choices = notification_choices
        notification_field.initial = notification_initial
        self.fields.keyOrder = ['first_name', 'last_name', 'username', 'email',
                                'password1', 'password2', 'old_password',
                                'logo', 'description', 'location', 'website',
                                'notifications']

    def clean_old_password(self):
        old_password = self.cleaned_data["old_password"]
        if set(self.changed_data) & set(['password1', 'username', 'email']):
            if old_password == '':
                raise ValidationError(_("You must enter your old password to "
                                        "change your password, username, or "
                                        "email."))
            elif not self.instance.check_password(old_password):
                raise ValidationError(_("Your old password was entered "
                                        "incorrectly. Please enter it again."))
        return old_password

    def save_notifications(self):
        notice_type_pks = [int(pk) for pk in self.cleaned_data['notifications']]
        notice_settings = NoticeSetting.objects.filter(user=self.instance)

        for notice_setting in notice_settings:
            send = notice_setting.notice_type_id in notice_type_pks
            if send != notice_setting.send:
                notice_setting.send = send
                notice_setting.save()

    def save(self, commit=True):
        instance = super(ProfileForm, self).save(commit)
        if commit:
            self.save_notifications()
        return instance


class AdminUserForm(BaseUserForm):
    """Form for an admin to edit a user's profile."""
    role = forms.ChoiceField(choices=(
            ('user', 'User'),
            ('admin', 'Admin')),
            widget=forms.RadioSelect,
            required=False, initial='user')

    def __init__(self, *args, **kwargs):
        super(AdminUserForm, self).__init__(*args, **kwargs)
        self.sitelocation = SiteLocation.objects.get_current()
        self.fields.keyOrder = ['first_name', 'last_name', 'username', 'email',
                                'password1', 'password2', 'logo', 'description',
                                'location', 'website', 'role']
        if self.profile.user_id:
            if self.sitelocation.user_is_admin(self.profile.user):
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
        instance = super(AdminUserForm, self).save(commit=False)

        if created and not self.cleaned_data['password1']:
            instance.set_unusable_password()

        old_save_m2m = self.save_m2m
        def save_m2m():
            old_save_m2m()

            if self.cleaned_data['role'] == 'admin':
                if not instance.is_superuser:
                    self.sitelocation.admins.add(instance)
            else:
                self.sitelocation.admins.remove(instance)

        if commit:
            instance.save()
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return instance
