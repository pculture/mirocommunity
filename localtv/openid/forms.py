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

