from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    ChangeField('Video', 'feed', initial=None, null=True)
]
