from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Feed', 'auto_categories',
             models.ManyToManyField, related_model='localtv.Category'),
    AddField('Feed', 'auto_authors', models.ManyToManyField,
             related_model='localtv.Author')
]
