from django.db import models
from django.contrib import admin


class Profile(models.Model):
    """
    Some extra data that we store about users.  Gets linked to a User object
    through the Django authentication system.
    """
    user = models.ForeignKey('auth.User')
    logo = models.ImageField(upload_to="localtv/profile_logos", blank=True,
                             verbose_name='Image')
    location = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField(blank=True, default='')
    website = models.URLField(blank=True, default='')

    class Meta:
        db_table = 'localtv_profile'

    def __unicode__(self):
        return unicode(self.user)


admin.site.register(Profile)
