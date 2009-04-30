from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Video', 'has_thumbnail', models.BooleanField, initial=False),
    AddField('Video', 'thumbnail_url', models.URLField,
             initial='', max_length=400),
    AddField('Video', 'thumbnail_extension', models.CharField,
             initial='', max_length=8)
]
