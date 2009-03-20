from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Video', 'guid', models.CharField, initial='',
             max_length=250),
]
