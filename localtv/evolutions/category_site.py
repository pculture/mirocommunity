from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    ChangeField('Category', 'site', initial=None, related_model='sites.Site')
]
