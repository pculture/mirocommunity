from django import forms

class FeedNameForm(forms.Form):
    name = forms.CharField(max_length=250)
