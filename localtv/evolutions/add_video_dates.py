from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Video', 'when_approved', models.DateTimeField, null=True),
    AddField('Video', 'when_published', models.DateTimeField, null=True),
]
