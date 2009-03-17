from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Video', 'embed_code', models.TextField, initial='')
]
