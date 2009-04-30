import urllib
import Image
import StringIO

from django.db import models
from django.contrib import admin
from django.contrib.sites.models import Site
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


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


VIDEO_THUMB_SIZES = [
    (142, 104)]


class Error(Exception): pass
class CannotOpenImageUrl(Error): pass


class OpenIdUser(models.Model):
    url = models.URLField(verify_exists=False, unique=True)
    email = models.EmailField()
    nickname = models.CharField(max_length=50, blank=True)
    status = models.IntegerField(
        choices=OPENID_STATUSES, default=OPENID_STATUS_ACTIVE)
    superuser = models.BooleanField()

    def __unicode__(self):
        return "%s <%s>" % (self.nickname, self.email)


class SiteLocation(models.Model):
    site = models.ForeignKey(Site, unique=True)
    # logo... we can probably be lazy and just link this as part of the id..
    admins = models.ManyToManyField(OpenIdUser, null=True, blank=True)
    status = models.IntegerField(
        choices=SITE_STATUSES, default=SITE_STATUS_ACTIVE)
    sidebar_html = models.TextField(blank=True)
    tagline = models.CharField(max_length=250, blank=True)
    
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
    feed_url = models.URLField(verify_exists=False)
    site = models.ForeignKey(Site)
    name = models.CharField(max_length=250)
    webpage = models.URLField(verify_exists=False, blank=True)
    description = models.TextField()
    last_updated = models.DateTimeField()
    when_submitted = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=FEED_STATUSES)
    etag = models.CharField(max_length=250, blank=True)
    auto_approve = models.BooleanField(default=False)

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
    """
    Fields:
     - name: Name of this video
     - site: Site this video is attached to
     - description: Video description
     - tags: A list of Tag objects associated with this item
     - categories: Similar to Tags
     - file_url: The file this object points to (if any) ... if not
       provided, at minimum we need the embed_code for the item.
     - when_submitted: When this item was first entered into the
       database
     - when_approved: When this item was marked to appear publicly on
       the site
     - when_published: When this file was published at its original
       source (if known)
     - status: one of localtv.models.VIDEOS_STATUSES
     - feed: which feed this item came from (if any)
     - website_url: The page that this item is associated with.
     - embed_code: code used to embed this item
     - guid: data used
    """
    name = models.CharField(max_length=250)
    site = models.ForeignKey(Site)
    description = models.TextField()
    tags = models.ManyToManyField(Tag, blank=True)
    categories = models.ManyToManyField(Category, blank=True)
    file_url = models.URLField(verify_exists=False, blank=True)
    when_submitted = models.DateTimeField(auto_now_add=True)
    when_approved = models.DateTimeField(null=True, blank=True)
    when_published = models.DateTimeField(null=True, blank=True)
    last_featured = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(
        choices=VIDEO_STATUSES, default=VIDEO_STATUS_UNAPPROVED)
    feed = models.ForeignKey(Feed, null=True, blank=True)
    website_url = models.URLField(verify_exists=False, blank=True)
    embed_code = models.TextField(blank=True)
    guid = models.CharField(max_length=250, blank=True)
    has_thumbnail = models.BooleanField(default=False)
    thumbnail_url = models.URLField(
        verify_exists=False, blank=True, max_length=400)
    thumbnail_extension = models.CharField(max_length=8, blank=True)

    class Meta:
        ordering = ['-when_submitted']

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_view_video', (),
                {'video_id': self.id})

    def save_thumbnail(self):
        if not self.thumbnail_url:
            return

        content_thumb = ContentFile(urllib.urlopen(self.thumbnail_url).read())

        try:
            pil_image = Image.open(content_thumb.file)
        except IOError:
            raise CannotOpenImageUrl(
                'An image at the url %s could not be loaded' % (
                    self.thumbnail_url))

        self.thumbnail_extension = pil_image.format.lower()

        # save an unresized version, overwriting if necessary
        default_storage.delete(
            self.get_original_thumb_storage_path())
        default_storage.save(
            self.get_original_thumb_storage_path(),
            content_thumb)

        # save any resized versions
        self.resize_thumbnail(pil_image)
        self.has_thumbnail = True
        self.save()

    def resize_thumbnail(self, thumb=None):
        if not thumb:
            thumb = Image.open(
                default_storage.open(self.get_original_thumb_storage_path()))

        for width, height in VIDEO_THUMB_SIZES:
            resized_image = thumb.resize((width, height), Image.ANTIALIAS)
            sio_img = StringIO.StringIO()
            resized_image.save(sio_img, 'png')
            sio_img.seek(0)
            cf_image = ContentFile(sio_img.read())

            # write file, deleting old thumb if it exists
            default_storage.delete(
                self.get_resized_thumb_storage_path(width, height))
            default_storage.save(
                self.get_resized_thumb_storage_path(width, height),
                cf_image)

    def get_original_thumb_storage_path(self):
        return 'localtv/video_thumbs/%s/orig.%s' % (
            self.id, self.thumbnail_extension)

    def get_resized_thumb_storage_path(self, width, height):
        return 'localtv/video_thumbs/%s/%sx%s.png' % (
            self.id, width, height)


class VideoAdmin(admin.ModelAdmin):
    list_display = ('name', 'site', 'when_submitted', 'status', 'feed')
    list_filter = ['status', 'when_submitted']
    search_fields = ['name', 'description']


class SavedSearch(models.Model):
    site = models.ForeignKey(SiteLocation)
    query_string = models.TextField()
    when_created = models.DateTimeField()


admin.site.register(OpenIdUser)
admin.site.register(SiteLocation)
admin.site.register(SiteCss)
admin.site.register(Tag)
admin.site.register(Feed)
admin.site.register(Category)
admin.site.register(Video, VideoAdmin)
admin.site.register(SavedSearch)
