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

SITE_STATUS_DISABLED = 0
SITE_STATUS_ACTIVE = 1

SITE_STATUSES = (
    (SITE_STATUS_DISABLED, 'Disabled'),
    (SITE_STATUS_ACTIVE, 'Active'))

OPENID_STATUS_DISABLED = 0
OPENID_STATUS_ACTIVE = 1

OPENID_STATUSES = (
    (OPENID_STATUS_DISABLED, 'Disabled'),
    (OPENID_STATUS_ACTIVE, 'Active'))


class OpenIdUser(models.Model):
    url = models.URLField(unique=True)
    email = models.EmailField()
    nickname = models.CharField(max_length=50, blank=True)
    status = models.IntegerField(
        choices=OPENID_STATUSES, default=OPENID_STATUS_ACTIVE)

    def __unicode__(self):
        return "%s <%s>" % (self.nickname, self.email)


class SiteLocation(models.Model):
    site = models.ForeignKey(Site, unique=True)
    # logo... we can probably be lazy and just link this as part of the id..
    admins = models.ManyToManyField(User, null=True)
    status = models.IntegerField(
        choices=SITE_STATUSES, default=SITE_STATUS_ACTIVE)
    sidebar_html = models.TextField(null=True)
    tagline = models.CharField(max_length=250, null=True)
    
    def __unicode__(self):
        return self.site.name


class SiteCss(models.Model):
    name = models.CharField(max_length=250)
    css = models.TextField()

    def __unicode__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=25)

    def __unicode__(self):
        return self.name


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

    def __unicode__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=80)

    def __unicode__(self):
        return self.name


class Video(models.Model):
    name = models.CharField(max_length=250)
    site = models.ForeignKey(Site)
    description = models.TextField()
    tags = models.ManyToManyField(Tag, null=True)
    categories = models.ManyToManyField(Category)
    file_url = models.URLField()
    # submitter <- should be link to an openid object
    when_submitted = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(
        choices=VIDEO_STATUSES, default=VIDEO_STATUS_UNAPPROVED)
    feed = models.ForeignKey(Feed, null=True, blank=True)
    website_url = models.URLField(null=True)

    def __unicode__(self):
        return self.name


admin.site.register(OpenIdUser)
admin.site.register(SiteLocation)
admin.site.register(SiteCss)
admin.site.register(Tag)
admin.site.register(Feed)
admin.site.register(Category)
admin.site.register(Video)

