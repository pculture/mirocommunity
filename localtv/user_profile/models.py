import urllib

from django.core.files.base import ContentFile
from django.db import models
from django.db.models import signals
from django.contrib import admin

from socialauth.models import TwitterUserProfile, FacebookUserProfile

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

def twitteruserprofile_created(sender, instance=None, raw=None, created=False,
                               **kwargs):
    if not created:
        return # we don't care about updates
    profile = Profile.objects.create(
        user=instance.user,
        location=instance.location or '',
        description=instance.description or '',
        website=instance.url or '')
    if instance.profile_image_url:
        try:
            cf = ContentFile(urllib.urlopen(
                    instance.profile_image_url).read())
        except Exception:
            pass
        else:
            cf.name = instance.profile_image_url
            profile.logo = cf
            profile.save()


def facebookuserprofile_created(sender, instance=None, raw=None, created=False,
                                **kwargs):
    if not created:
        return # we don't care about updates
    Profile.objects.create(
        user=instance.user,
        location=instance.location or '',
        description=instance.about_me or '',
        website=instance.url or '')

signals.post_save.connect(twitteruserprofile_created,
                          sender=TwitterUserProfile)
signals.post_save.connect(facebookuserprofile_created,
                          sender=FacebookUserProfile)
