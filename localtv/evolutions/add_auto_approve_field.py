from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Feed', 'auto_approve', models.BooleanField, initial=False)
]
