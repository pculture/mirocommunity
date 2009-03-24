from django_evolution.mutations import *
from django.db import models

# Note on this one:
#
# There seems to be a bug with sqlite on this evolution where it sets
# the localtv_video table to be entirely of the value "localtv_video"
# (as in, the string!)
#
# You may have to run this after evolving:
# sqlite> update localtv_video set last_featured=NULL;

MUTATIONS = [
    AddField('Video', 'last_featured', models.DateTimeField, null=True)
]
