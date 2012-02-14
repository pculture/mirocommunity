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

from localtv.models import SiteLocation


class SettingsForm(forms.ModelForm):
    title = forms.CharField(label="Site Title", max_length=50)

    class Meta:
        model = SiteLocation
        exclude = ['site', 'status', 'admins', 'tier_name', 'hide_get_started']


    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        if self.instance:
            self.initial['title'] = self.instance.site.name
        if (not SiteLocation.enforce_tiers()
            or localtv.tiers.Tier.get().permit_custom_css()):
            pass # Sweet, CSS is permitted.
        else:
            # Uh-oh: custom CSS is not permitted!
            #
            # To handle only letting certain paid users edit CSS,
            # we do two things.
            #
            # 1. Cosmetically, we set the CSS editing box's CSS class
            # to be 'hidden'. (We have some CSS that makes it not show
            # up.)
            css_field = self.fields['css']
            css_field.label += ' (upgrade to enable this form field)'
            css_field.widget.attrs['readonly'] = True
            #
            # 2. In validation, we make sure that changing the CSS is
            # rejected as invalid if the site does not have permission
            # to do that.

    def clean_css(self):
        css = self.cleaned_data.get('css')
        # Does thes SiteLocation permit CSS modifications? If so,
        # return the data the user inputted.
        if (not SiteLocation.enforce_tiers() or
            localtv.tiers.Tier.get().permit_custom_css()):
            return css # no questions asked

        # We permit the value if it's the same as self.instance has:
        if self.instance.css == css:
            return css

        # Otherwise, reject the change.
        self.data['css'] = self.instance.css
        raise ValidationError("To edit CSS for your site, you have to upgrade.")

    def save(self):
        sitelocation = forms.ModelForm.save(self)
        if sitelocation.logo:
            sitelocation.logo.open()
            cf = ContentFile(sitelocation.logo.read())
            sitelocation.save_thumbnail_from_file(cf)
        sitelocation.site.name = self.cleaned_data['title']
        sitelocation.site.save()
        SiteLocation.objects.clear_cache()
        return sitelocation