from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Video', 'authors', models.ManyToManyField, related_model='localtv.Author')
]
