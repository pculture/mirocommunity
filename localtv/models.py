from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.sites.models import Site


VIDEO_STATUS_UNAPPROVED = FEED_STATUS_UNAPPROVED =0
VIDEO_STATUS_ACTIVE = FEED_STATUS_ACTIVE = 1
VIDEO_STATUS_REJECTED = FEED_STATUS_REJECTED = 2

VIDEO_STATUSES = FEED_STATUSES = (
    (VIDEO_STATUS_UNAPPROVED, 'Unapproved'),
    (VIDEO_STATUS_ACTIVE, 'Active'),
    (VIDEO_STATUS_REJECTED, 'Rejected'))

SITE_STATUS_INACTIVE = 0
SITE_STATUS_ACTIVE = 1

SITE_STATUSES = (
    (SITE_STATUS_INACTIVE, 'Inactive'),
    (SITE_STATUS_ACTIVE, 'Active'))


class SiteLocation(models.Model):
    site = models.ForeignKey(Site, unique=True)
    name = models.CharField(max_length=250, unique=True)
    # logo... we can probably be lazy and just link this as part of the id..
    slug = models.SlugField()
    admins = models.ManyToManyField(User)
    status = models.IntegerField(
        choices=SITE_STATUSES, default=SITE_STATUS_ACTIVE)
    

class SiteCss(models.Model):
    name = models.CharField(max_length=250)
    css = models.TextField()


class Tag(models.Model):
    name = models.CharField(max_length=25)


class Feed(models.Model):
    feed_url = models.URLField()
    site = models.ForeignKey(Site, unique=True)
    name = models.CharField(max_length=250)
    webpage = models.URLField(null=True)
    description = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)
    when_submitted = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=FEED_STATUSES)
    etag = models.CharField(max_length=250)
    # should name and site be unique together too?

    class Meta:
        unique_together = (
            ('feed_url', 'site'),
            ('name', 'site'))


class Category(models.Model):
    name = models.CharField(max_length=80)


class Video(models.Model):
    name = models.CharField(max_length=250)
    site = models.ForeignKey(Site)
    description = models.TextField()
    tags = models.ManyToManyField(Tag)
    categories = models.ManyToManyField(Category)
    file_url = models.URLField()
    # submitter <- should be link to an openid object
    when_submitted = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=VIDEO_STATUSES)
    feed = models.ForeignKey(Feed)
    website_url = models.URLField(null=True)


#class Profile(models.Model):
# make openid profiles here later

admin.site.register(SiteLocation)
admin.site.register(SiteCss)
admin.site.register(Tag)
admin.site.register(Feed)
admin.site.register(Category)
admin.site.register(Video)

