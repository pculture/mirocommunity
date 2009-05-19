from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Video', 'file_url_length', models.IntegerField, null=True),
    AddField(
        'Video', 'file_url_mimetype',
        models.CharField, initial='', max_length=60)
]
