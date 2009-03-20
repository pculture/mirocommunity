from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    ChangeField('Feed', 'site', initial=None, unique=False)
]
