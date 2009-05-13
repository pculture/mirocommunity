from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Video', 'flash_enclosure_url',
             models.URLField, initial='', max_length=200)
]
