from django import forms

class OpenIdRegistrationForm(forms.Form):
    # we don't really need the openid url since that's in the session..
    email = forms.EmailField()
    nickname = forms.CharField()
