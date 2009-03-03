from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('OpenIdUser', 'nickname', models.CharField, initial="", max_length=50),
    AddField('OpenIdUser', 'email', models.EmailField, initial="", max_length=75)
]
#----------------------
