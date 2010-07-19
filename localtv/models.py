
# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import httplib
import re
import urllib
import urllib2
import urlparse
import Image
import StringIO
from xml.sax.saxutils import unescape
from BeautifulSoup import BeautifulSoup

from django.db import models
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.comments.moderation import CommentModerator, moderator
from django.contrib.sites.models import Site
from django.core import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.core.signals import request_finished
import django.dispatch
try:
    from django.core.validators import ipv4_re # Django 1.2+
except ImportError:
    from django.forms.fields import ipv4_re # Django 1.1
from django.template import mark_safe, Context, loader
from django.template.defaultfilters import slugify

import bitly
import feedparser
import vidscraper
from notification import models as notification
import tagging

from localtv.templatetags.filters import sanitize
from localtv import util

# the difference between unapproved and rejected is that unapproved simply
# hasn't been looked at by an administrator yet.
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

THUMB_SIZES = [
    (534, 430), # behind a video
    (375, 295), # featured on frontpage
    (140, 110),
    (364, 271), # main thumb
    (222, 169), # medium thumb
    (88, 68),   # small thumb
    ]

VIDEO_SERVICE_REGEXES = (
    ('YouTube', r'http://gdata\.youtube\.com/feeds/'),
    ('YouTube', r'http://(www\.)?youtube\.com/'),
    ('blip.tv', r'http://(.+\.)?blip\.tv/'),
    ('Vimeo', r'http://(www\.)?vimeo\.com/'),
    ('Dailymotion', r'http://(www\.)?dailymotion\.com/rss'))

class Error(Exception): pass
class CannotOpenImageUrl(Error): pass


class BitLyWrappingURLField(models.URLField):
    def get_db_prep_value(self, value):
        if not settings.BITLY_LOGIN:
            return value
        if len(value) <= self.max_length: # short enough to save
            return value
        api = bitly.Api(login=settings.BITLY_LOGIN,
                        apikey=settings.BITLY_API_KEY)
        try:
            return unicode(api.shorten(value))
        except bitly.BitlyError:
            return unicode(value)[:self.max_length]


class Thumbnailable(models.Model):
    """
    A type of Model that has thumbnails generated for it.
    """
    has_thumbnail = models.BooleanField(default=False)
    thumbnail_extension = models.CharField(max_length=8, blank=True)

    class Meta:
        abstract = True

    _thumbnail_force_height = True # make sure the thumbnail is the correct
                                   # size

    def save_thumbnail_from_file(self, content_thumb):
        """
        Takes an image file-like object and stores it as the thumbnail for this
        video item.
        """
        try:
            pil_image = Image.open(content_thumb)
        except IOError:
            raise CannotOpenImageUrl('An image could not be loaded')

        self.thumbnail_extension = pil_image.format.lower()

        # save an unresized version, overwriting if necessary
        default_storage.delete(
            self.get_original_thumb_storage_path())
        default_storage.save(
            self.get_original_thumb_storage_path(),
            content_thumb)

        if hasattr(content_thumb, 'temporary_file_path'):
            # might have gotten moved by Django's storage system, so it might
            # be invalid now.  to make sure we've got a valid file, we reopen
            # under the new path
            content_thumb.close()
            content_thumb = default_storage.open(
                self.get_original_thumb_storage_path())
            pil_image = Image.open(content_thumb)

        # save any resized versions
        self.resize_thumbnail(pil_image)
        self.has_thumbnail = True
        self.save()

    def resize_thumbnail(self, thumb=None):
        """
        Creates resized versions of the video's thumbnail image
        """
        if not thumb:
            thumb = Image.open(
                default_storage.open(self.get_original_thumb_storage_path()))
        for width, height in THUMB_SIZES:
            resized_image = thumb.copy()
            if resized_image.size != (width, height):
                width_scale = float(resized_image.size[0]) / width
                if self._thumbnail_force_height:
                    # make the resized_image have one side the same as the
                    # thumbnail, and the other bigger so we can crop it
                    height_scale = float(resized_image.size[1]) / height
                    if width_scale < height_scale:
                        new_height = int(resized_image.size[1] / width_scale)
                        new_width = width
                    else:
                        new_width = int(resized_image.size[0] / height_scale)
                        new_height = height
                    resized_image = resized_image.resize(
                        (new_width, new_height),
                        Image.ANTIALIAS)
                    if resized_image.size != (width, height):
                        x = y = 0
                        if resized_image.size[1] > height:
                            y = int((height - resized_image.size[1]) / 2)
                        else:
                            x = int((width - resized_image.size[0]) / 2)
                        new_image = Image.new('RGBA',
                                              (width, height), (0, 0, 0, 0))
                        new_image.paste(resized_image, (x, y))
                        resized_image = new_image
                elif width_scale > 1:
                    # resize the width, keep the height aspect ratio the same
                    new_height = int(resized_image.size[1] / width_scale)
                    resized_image = resized_image.resize((width, new_height),
                                                         Image.ANTIALIAS)
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
        """
        Return the path for the original thumbnail, relative to the default
        file storage system.
        """
        return 'localtv/%s_thumbs/%s/orig.%s' % (
            self._meta.object_name.lower(),
            self.id, self.thumbnail_extension)

    def get_resized_thumb_storage_path(self, width, height):
        """
        Return the path for the a thumbnail of a resized width and height,
        relative to the default file storage system.
        """
        return 'localtv/%s_thumbs/%s/%sx%s.png' % (
            self._meta.object_name.lower(),
            self.id, width, height)

    def delete_thumbnails(self):
        self.has_thumbnail = False
        default_storage.delete(self.get_original_thumb_storage_path())
        for size in THUMB_SIZES:
            default_storage.delete(self.get_resized_thumb_storage_path(*size))
        self.thumbnail_extension = ''
        self.save()

    def delete(self, *args, **kwargs):
        self.delete_thumbnails()
        super(Thumbnailable, self).delete(*args, **kwargs)



SITE_LOCATION_CACHE = {}

class SiteLocationManager(models.Manager):
    def get_current(self):
        sid = settings.SITE_ID
        try:
            current_site_location = SITE_LOCATION_CACHE[sid]
        except KeyError:
            current_site_location = self.select_related().get(site__pk=sid)
            SITE_LOCATION_CACHE[sid] = current_site_location
        return current_site_location

    def get(self, **kwargs):
        if 'site' in kwargs:
            site= kwargs.pop('site')
            if not isinstance(site, (int, long, basestring)):
                site = site.id
            site = int(site)
            try:
                return SITE_LOCATION_CACHE[site]
            except KeyError:
                pass
        site_location = models.Manager.get(self, **kwargs)
        SITE_LOCATION_CACHE[site_location.site_id] = site_location
        return site_location

    def clear_cache(self):
        global SITE_LOCATION_CACHE
        SITE_LOCATION_CACHE = {}


class SiteLocation(Thumbnailable):
    """
    An extension to the django.contrib.sites site model, providing
    localtv-specific data.

    Fields:
     - site: A link to the django.contrib.sites.models.Site object
     - logo: custom logo image for this site
     - background: custom background image for this site (unused?)
     - admins: a collection of Users who have access to administrate this
       sitelocation
     - status: one of SITE_STATUSES; either disabled or active
     - sidebar_html: custom html to appear on the right sidebar of many
       user-facing pages.  Can be whatever's most appropriate for the owners of
       said site.
     - footer_html: HTML that appears at the bottom of most user-facing pages.
       Can be whatever's most appropriate for the owners of said site.
     - about_html: HTML to display on the s about page
     - tagline: displays below the s title on most user-facing pages
     - css: The intention here is to allow  to paste in their own CSS
       here from the admin.  Not used presently, though eventually it should
       be.
     - display_submit_button: whether or not we should allow users to see that
       they can submit videos or not (doesn't affect whether or not they
       actually can though)
     - submission_requires_login: whether or not users need to log in to submit
       videos.
    """
    site = models.ForeignKey(Site, unique=True)
    logo = models.ImageField(upload_to='localtv/site_logos', blank=True)
    background = models.ImageField(upload_to='localtv/site_backgrounds',
                                   blank=True)
    admins = models.ManyToManyField('auth.User', blank=True,
                                    related_name='admin_for')
    status = models.IntegerField(
        choices=SITE_STATUSES, default=SITE_STATUS_ACTIVE)
    sidebar_html = models.TextField(blank=True)
    footer_html = models.TextField(blank=True)
    about_html = models.TextField(blank=True)
    tagline = models.CharField(max_length=250, blank=True)
    css = models.TextField(blank=True)
    display_submit_button = models.BooleanField(default=True)
    submission_requires_login = models.BooleanField(default=False)

    # ordering options
    use_original_date = models.BooleanField(
        default=True,
        help_text="If set, use the original date the video was posted.  "
        "Otherwise, use the date the video was added to this site.")

    # comments options
    screen_all_comments = models.BooleanField(
        verbose_name='Hold comments for moderation',
        default=True,
        help_text="Hold all comments for moderation by default?")
    comments_required_login = models.BooleanField(
        default=False,
        verbose_name="Require Login",
        help_text="If True, comments require the user to be logged in.")

    objects = SiteLocationManager()

    _thumbnail_force_height = False

    def __unicode__(self):
        return '%s (%s)' % (self.site.name, self.site.domain)

    def user_is_admin(self, user):
        """
        Return True if the given User is an admin for this SiteLocation.
        """
        if not user.is_authenticated() or not user.is_active:
            return False

        if user.is_superuser:
            return True

        return bool(self.admins.filter(pk=user.pk).count())

    def save(self, *args, **kwargs):
        SITE_LOCATION_CACHE[self.pk] = self
        return models.Model.save(self, *args, **kwargs)

class Source(Thumbnailable):
    """
    An abstract base class to represent things which are sources of multiple
    videos.  Current subclasses are Feed and SavedSearch.
    """
    id = models.AutoField(primary_key=True)
    site = models.ForeignKey(Site)
    auto_approve = models.BooleanField(default=False)
    user = models.ForeignKey('auth.User', null=True, blank=True)
    auto_categories = models.ManyToManyField("Category", blank=True)
    auto_authors = models.ManyToManyField("auth.User", blank=True,
                                          related_name='auto_%(class)s_set')

    class Meta:
        abstract = True

class Feed(Source):
    """
    Feed to pull videos in from.

    If the same feed is used on two different , they will require two
    separate entries here.

    Fields:
      - feed_url: The location of this field
      - site: which site this feed belongs to
      - name: human readable name for this feed
      - webpage: webpage that this feed\'s content is associated with
      - description: human readable description of this item
      - last_updated: last time we ran self.update_items()
      - when_submitted: when this feed was first registered on this site
      - status: one of FEED_STATUSES, either unapproved, active, or rejected
      - etag: used to see whether or not the feed has changed since our last
        update.
      - auto_approve: whether or not to set all videos in this feed to approved
        during the import process
      - user: a user that submitted this feed, if any
      - auto_categories: categories that are automatically applied to videos on
        import
      - auto_authors: authors that are automatically applied to videos on
        import
    """
    feed_url = models.URLField(verify_exists=False)
    name = models.CharField(max_length=250)
    webpage = models.URLField(verify_exists=False, blank=True)
    description = models.TextField()
    last_updated = models.DateTimeField()
    when_submitted = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=FEED_STATUSES)
    etag = models.CharField(max_length=250, blank=True)

    class Meta:
        unique_together = (
            ('feed_url', 'site'))

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_list_feed', [self.pk])

    def update_items(self, verbose=False, parsed_feed=None,
                     clear_rejected=False):
        """
        Fetch and import new videos from this feed.

        If clear_rejected is True, rejected videos that are part of this
        feed will be deleted and re-imported.
        """
        for i in self._update_items_generator(verbose, parsed_feed,
                                              clear_rejected):
            pass

    def _update_items_generator(self, verbose=False, parsed_feed=None,
                                clear_rejected=False):
        """
        Fetch and import new videos from this field.  After each imported
        video, we yield a dictionary:
        {'index': the index of the video we've just imported,
         'total': the total number of videos in the feed,
         'video': the Video object we just imported
        }
        """
        if self.auto_approve:
            initial_video_status = VIDEO_STATUS_ACTIVE
        else:
            initial_video_status = VIDEO_STATUS_UNAPPROVED

        if parsed_feed is None:
            parsed_feed = feedparser.parse(self.feed_url, etag=self.etag)

        for index, entry in enumerate(parsed_feed['entries'][::-1]):
            skip = False
            guid = entry.get('guid', '')
            if guid and Video.objects.filter(
                feed=self, guid=guid).count():
                skip = 'duplicate guid'
            link = entry.get('link', '')
            for possible_link in entry.links:
                if possible_link.get('rel') == 'via':
                    # original URL
                    link = possible_link['href']
                    break
            if link:
                if clear_rejected:
                    for video in Video.objects.filter(
                        status=VIDEO_STATUS_REJECTED,
                        website_url=link):
                        video.delete()
                if Video.objects.filter(
                    website_url=link).count():
                    skip = 'duplicate link'

            video_data = {
                'name': unescape(entry['title']),
                'guid': guid,
                'site': self.site,
                'description': '',
                'file_url': '',
                'file_url_length': None,
                'file_url_mimetype': '',
                'embed_code': '',
                'flash_enclosure_url': '',
                'when_submitted': datetime.datetime.now(),
                'when_approved': (
                    self.auto_approve and datetime.datetime.now() or None),
                'status': initial_video_status,
                'when_published': None,
                'feed': self,
                'website_url': link}

            tags = []
            authors = self.auto_authors.all()

            if 'updated_parsed' in entry:
                video_data['when_published'] = datetime.datetime(
                    *entry.updated_parsed[:6])

            thumbnail_url = util.get_thumbnail_url(entry) or ''
            if thumbnail_url and not urlparse.urlparse(thumbnail_url)[0]:
                thumbnail_url = urlparse.urljoin(parsed_feed.feed.link,
                                                 thumbnail_url)
            video_data['thumbnail_url'] = thumbnail_url

            video_enclosure = util.get_first_video_enclosure(entry)
            if video_enclosure:
                file_url = video_enclosure.get('url')
                if file_url:
                    file_url = unescape(file_url)
                    if not urlparse.urlparse(file_url)[0]:
                        file_url = urlparse.urljoin(parsed_feed.feed.link,
                                                    file_url)
                    video_data['file_url'] = file_url

                    try:
                        file_url_length = int(
                            video_enclosure.get('filesize') or
                            video_enclosure.get('length'))
                    except (ValueError, TypeError):
                        file_url_length = None
                    video_data['file_url_length'] = file_url_length

                    video_data['file_url_mimetype'] = video_enclosure.get(
                        'type')

            if link and not skip:
                try:
                    scraped_data = vidscraper.auto_scrape(
                        link,
                        fields=['file_url', 'embed', 'flash_enclosure_url',
                                'publish_date', 'thumbnail_url', 'link',
                                'file_url_is_flaky', 'user', 'user_url',
                                'tags', 'description'])
                    if not video_data['file_url']:
                        if not scraped_data.get('file_url_is_flaky'):
                            video_data['file_url'] = scraped_data.get(
                                'file_url') or ''
                    video_data['embed_code'] = scraped_data.get('embed')
                    video_data['flash_enclosure_url'] = scraped_data.get(
                        'flash_enclosure_url', '')
                    video_data['when_published'] = scraped_data.get(
                        'publish_date')
                    video_data['description'] = scraped_data.get(
                        'description', '')
                    if scraped_data['thumbnail_url']:
                        video_data['thumbnail_url'] = scraped_data.get(
                            'thumbnail_url')

                    if scraped_data.get('link'):
                        if (Video.objects.filter(
                                website_url=scraped_data['link']).count()):
                            skip = 'duplicate link (vidscraper)'
                        else:
                            video_data['website_url'] = scraped_data['link']

                    tags = scraped_data.get('tags', [])

                    if not authors.count() and scraped_data.get('user'):
                        author, created = User.objects.get_or_create(
                            username=scraped_data.get('user'),
                            defaults={'first_name': scraped_data.get('user')})
                        if created:
                            author.set_unusable_password()
                            author.save()
                            util.get_profile_model().objects.create(
                                user=author,
                                website=scraped_data.get('user_url'))
                        authors = [author]

                except vidscraper.errors.Error, e:
                    if verbose:
                        print "Vidscraper error: %s" % e

            if not skip:
                if not (video_data['file_url'] or video_data['embed_code']):
                    skip = 'invalid'

            if skip:
                if verbose:
                    print "Skipping %s: %s" % (entry['title'], skip)
                yield {'index': index,
                       'total': len(parsed_feed.entries),
                       'video': None,
                       'skip': skip}
                continue

            if not video_data['description']:
                description = entry.get('summary', '')
                for content in entry.get('content', []):
                    type = content.get('type', '')
                    if 'html' in type:
                        description = content.value
                        break
                video_data['description'] = description

            if video_data['description']:
                soup = BeautifulSoup(video_data['description'])
                for tag in soup.findAll(
                    'div', {'class': "miro-community-description"}):
                    video_data['description'] = tag.renderContents()
                    break
                video_data['description'] = sanitize(video_data['description'],
                                                     extra_filters=['img'])

            if entry.get('media_player'):
                player = entry['media_player']
                if isinstance(player, basestring):
                    video_data['embed_code'] = unescape(player)
                elif player.get('content'):
                    video_data['embed_code'] = unescape(player['content'])
                elif 'url' in player and not video_data['embed_code']:
                    video_data['embed_code'] = '<embed src="%(url)s">' % player

            video = Video.objects.create(**video_data)
            if verbose:
                    print 'Made video %i: %s' % (video.pk, video.name)

            try:
                video.save_thumbnail()
            except CannotOpenImageUrl:
                if verbose:
                    print "Can't get the thumbnail for %s at %s" % (
                        video.id, video.thumbnail_url)

            if entry.get('tags') or tags:
                if not tags:
                    tags = set(
                        tag['term'] for tag in entry['tags']
                        if tag.get('term'))
                if tags:
                    video.tags = util.get_or_create_tags(tags)

            video.categories = self.auto_categories.all()
            video.authors = authors
            video.save()

            yield {'index': index,
                   'total': len(parsed_feed.entries),
                   'video': video}

        self.etag = parsed_feed.get('etag') or ''
        self.last_updated = datetime.datetime.now()
        self.save()

    def source_type(self):
        video_service = self.video_service()
        if video_service is None:
            return u'Feed'
        else:
            return u'User: %s' % video_service

    def video_service(self):
        for service, regexp in VIDEO_SERVICE_REGEXES:
            if re.search(regexp, self.feed_url, re.I):
                return service


class Category(models.Model):
    """
    A category for videos to be contained in.

    Categoies and tags aren't too different functionally, but categories are
    more strict as they can't be defined by visitors.  Categories can also be
    hierarchical.

    Fields:
     - site: A link to the django.contrib.sites.models.Site object this object
       is bound to
     - name: Name of this category
     - slug: a slugified verison of the name, used to create more friendly URLs
     - logo: An image to associate with this category
     - description: human readable description of this item
     - parent: Reference to another Category.  Allows you to have heirarchical
       categories.
    """
    site = models.ForeignKey(Site)
    name = models.CharField(
        max_length=80, verbose_name='Category Name',
        help_text=("The name is used to identify the "
                   "category almost everywhere; for "
                   "example under the post or in the "
                   "category widget."))
    slug = models.SlugField(
        verbose_name='Category Slug',
        help_text=('The "slug" is the URL-friendly version '
                   "of the name.  It is usually lower-case "
                   "and contains only letters, numbers and "
                   "hyphens."))
    logo = models.ImageField(
        upload_to="localtv/category_logos", blank=True,
        verbose_name='Thumbnail/Logo',
        help_text=("For example: a leaf for 'environment' "
                   "or the logo of a university "
                   "department."))
    description = models.TextField(
        blank=True, verbose_name='Description (HTML)',
        help_text=("The description is not prominent "
                   "by default, but some themes may "
                   "show it."))
    parent = models.ForeignKey(
        'self', blank=True, null=True,
        related_name='child_set',
        verbose_name='Category Parent',
        help_text=("Categories, unlike tags, can have a "
                   "hierarchy."))

    class Meta:
        ordering = ['name']
        unique_together = (
            ('slug', 'site'),
            ('name', 'site'))

    def __unicode__(self):
        return self.name

    def depth(self):
        """
        Returns the number of parents this category has.  Used for indentation.
        """
        depth = 0
        parent = self.parent
        while parent is not None:
            depth += 1
            parent = parent.parent
        return depth

    def dashes(self):
        return mark_safe('&mdash;' * self.depth())

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_category', [self.slug])

    @classmethod
    def in_order(klass, sitelocation, initial=None):
        objects = []
        def accumulate(categories):
            for category in categories:
                objects.append(category)
                if category.child_set.count():
                    accumulate(category.child_set.all())
        if initial is None:
            initial = klass.objects.filter(site=sitelocation, parent=None)
        accumulate(initial)
        return objects

    def approved_set(self):
        categories = [self] + self.in_order(self.site, self.child_set.all())
        return Video.objects.new(status=VIDEO_STATUS_ACTIVE,
                                 categories__in=categories).distinct()
    approved_set = property(approved_set)

class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


class SavedSearch(Source):
    """
    A set of keywords to regularly pull in new videos from.

    There's an administrative interface for doing "live searches"

    Fields:
     - site: site this savedsearch applies to
     - query_string: a whitespace-separated list of words to search for.  Words
       starting with a dash will be processed as negative query terms
     - when_created: date and time that this search was saved.
    """
    query_string = models.TextField()
    when_created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.query_string

    def update_items(self, verbose=False):
        from localtv.admin import util as admin_util
        raw_results = vidscraper.metasearch.intersperse_results(
            admin_util.metasearch_from_querystring(
                self.query_string))

        raw_results = [admin_util.MetasearchVideo.create_from_vidscraper_dict(
                result) for result in raw_results]

        raw_results = admin_util.strip_existing_metasearchvideos(
            [result for result in raw_results if result is not None],
            self.site)

        if self.auto_approve:
            initial_status = VIDEO_STATUS_ACTIVE
        else:
            initial_status = VIDEO_STATUS_UNAPPROVED

        authors = self.auto_authors.all()

        for result in raw_results:
            video = result.generate_video_model(self.site,
                                                initial_status)
            video.search = self
            video.categories = self.auto_categories.all()
            if authors.count():
                video.authors = self.auto_authors.all()
            else:
                author, created = User.objects.get_or_create(
                    username=video.video_service_user,
                    defaults={'first_name': video.video_service_user})
                if created:
                    author.set_unusable_password()
                    author.save()
                    util.get_profile_model().objects.create(
                        user=author,
                        website=video.video_service_url)
                video.authors = [author]
            video.save()

    def source_type(self):
        return 'Search'


class VideoManager(models.Manager):

    def new(self, **kwargs):
        published = 'localtv_video.when_published,'
        if 'site' in kwargs:
            if not SiteLocation.objects.get(
                site=kwargs['site']).use_original_date:
                published = ''
        videos = self.extra(select={'best_date': """
COALESCE(%slocaltv_video.when_approved,
localtv_video.when_submitted)""" % published})
        return videos.filter(**kwargs).order_by('-best_date')

    def popular_since(self, delta, sitelocation, **kwargs):
        """
        Returns a QuerySet of the most popular videos in the previous C{delta)
        time.

        @type delta: L{datetime.timedelta)
        @type sitelocation: L{SiteLocation}
        """
        from localtv import util

        cache_key = 'videomanager.popular_since:%s:%s' % (
            hash(delta), sitelocation.site.domain)
        for k in sorted(kwargs.keys()):
            v = kwargs[k]
            if '__timestamp__' in k:
                now = datetime.datetime.now().replace(microsecond=0)
                v = v.replace(microsecond=0)
                v = hash(now - v)
            cache_key += ':%s-%s' % (k, v)
        ids = cache.cache.get(cache_key)
        if ids is None:
            try:
                earliest_time = datetime.datetime.now() - delta
            except OverflowError:
                earliest_time = datetime.datetime(1900, 1, 1)

            if sitelocation is not None:
                videos = self.filter(site=sitelocation.site)
            else:
                videos = self
            if kwargs:
                videos = videos.filter(**kwargs)
            videos = videos.extra(
                select={'watchcount':
                            """SELECT COUNT(*) FROM localtv_watch
WHERE localtv_video.id = localtv_watch.video_id AND
localtv_watch.timestamp > %s"""},
                select_params = (earliest_time,))
            if 'extra_where' in kwargs:
                where = kwargs.pop('extra_where')
                videos = videos.extra(where=where)
            videos = videos.order_by(
                    '-watchcount',
                    '-when_published',
                    '-when_approved').distinct()
            ids = [v[0] for v in videos.values_list('id', 'watchcount')]
            cache.cache.set(cache_key, ids,
                            timeout=getattr(settings,
                                            'LOCALTV_POPULAR_QUERY_TIMEOUT',
                                            120 * 60 # 120 minutes
                                            ))
        keys = [key for key in kwargs if '__' not in key]
        return util.MockQueryset(ids, self.model,
                                 dict((key, kwargs[key]) for key in keys)
                                 )


class Video(Thumbnailable):
    """
    Fields:
     - name: Name of this video
     - site: Site this video is attached to
     - description: Video description
     - tags: A list of Tag objects associated with this item
     - categories: Similar to Tags
     - authors: the person/people responsible for this video
     - file_url: The file this object points to (if any) ... if not
       provided, at minimum we need the embed_code for the item.
     - file_url_length: size of the file, in bytes
     - file_url_mimetype: mimetype of the file
     - when_submitted: When this item was first entered into the
       database
     - when_approved: When this item was marked to appear publicly on
       the site
     - when_published: When this file was published at its original
       source (if known)
     - last_featured: last time this item was featured.
     - status: one of localtv.models.VIDEOS_STATUSES
     - feed: which feed this item came from (if any)
     - website_url: The page that this item is associated with.
     - embed_code: code used to embed this item.
     - flash_enclosure_url: Crappy enclosure link that doesn't
       actually point to a url.. the kind crappy flash video sites
       give out when they don't actually want their enclosures to
       point to video files.
     - guid: data used to identify this video
     - has_thumbnail: whether or not this video has a thumbnail
     - thumbnail_url: url to the thumbnail, if such a thing exists
     - thumbnail_extension: extension of the *internal* thumbnail, saved on the
       server (usually paired with the id, so we can determine "1123.jpg" or
       "1186.png"
     - user: if not None, the user who submitted this video
     - search: if not None, the SavedSearch from which this video came
     - video_service_user: if not blank, the username of the user on the video
       service who owns this video.  We can figure out the service from the
       website_url.
     - contact: a free-text field for anonymous users to specify some contact
       info
     - notes: a free-text field to add notes about the video
    """
    name = models.CharField(max_length=250)
    site = models.ForeignKey(Site)
    description = models.TextField(blank=True)
    categories = models.ManyToManyField(Category, blank=True)
    authors = models.ManyToManyField('auth.User', blank=True,
                                     related_name='authored_set')
    file_url = BitLyWrappingURLField(verify_exists=False, blank=True)
    file_url_length = models.IntegerField(null=True, blank=True)
    file_url_mimetype = models.CharField(max_length=60, blank=True)
    when_modified = models.DateTimeField(auto_now=True,
                                         db_index=True,
                                         default=datetime.datetime.now)
    when_submitted = models.DateTimeField(auto_now_add=True)
    when_approved = models.DateTimeField(null=True, blank=True)
    when_published = models.DateTimeField(null=True, blank=True)
    last_featured = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(
        choices=VIDEO_STATUSES, default=VIDEO_STATUS_UNAPPROVED)
    feed = models.ForeignKey(Feed, null=True, blank=True)
    website_url = BitLyWrappingURLField(verbose_name='Website URL',
                                        verify_exists=False,
                                        blank=True)
    embed_code = models.TextField(blank=True)
    flash_enclosure_url = BitLyWrappingURLField(verify_exists=False,
                                                blank=True)
    guid = models.CharField(max_length=250, blank=True)
    thumbnail_url = models.URLField(
        verify_exists=False, blank=True, max_length=400)
    user = models.ForeignKey('auth.User', null=True, blank=True)
    search = models.ForeignKey(SavedSearch, null=True, blank=True)
    video_service_user = models.CharField(max_length=250, blank=True,
                                          default='')
    video_service_url = models.URLField(verify_exists=False, blank=True,
                                        default='')
    contact = models.CharField(max_length=250, blank=True,
                               default='')
    notes = models.TextField(blank=True)


    objects = VideoManager()

    class Meta:
        ordering = ['-when_submitted']

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_view_video', (),
                {'video_id': self.id,
                 'slug': slugify(self.name)[:30]})

    def try_to_get_file_url_data(self):
        """
        Do a HEAD request on self.file_url to find information about
        self.file_url_length and self.file_url_mimetype

        Note that while this method fills in those attributes, it does *NOT*
        run self.save() ... so be sure to do so after calling this method!
        """
        if not self.file_url:
            return

        request = urllib2.Request(util.quote_unicode_url(self.file_url))
        request.get_method = lambda: 'HEAD'
        try:
            http_file = urllib2.urlopen(request)
        except Exception:
            pass
        else:
            self.file_url_length = http_file.headers.get('content-length')
            self.file_url_mimetype = http_file.headers.get('content-type', '')

    def save_thumbnail(self):
        """
        Automatically run the entire file saving process... provided we have a
        thumbnail_url, that is.
        """
        if not self.thumbnail_url:
            return

        try:
            content_thumb = ContentFile(urllib.urlopen(
                    util.quote_unicode_url(self.thumbnail_url)).read())
        except IOError:
            raise CannotOpenImageUrl('IOError loading %s' % self.thumbnail_url)
        except httplib.InvalidURL:
            # if the URL isn't valid, erase it and move on
            self.thumbnail_url = ''
            self.has_thumbnail = False
            self.save()
        else:
            self.save_thumbnail_from_file(content_thumb)

    def source_type(self):
        if self.search:
            return 'Search: %s' % self.search
        elif self.feed:
            if self.feed.video_service():
                return 'User: %s: %s' % (
                    self.feed.video_service(),
                    self.feed)
            else:
                return 'Feed: %s' % self.feed
        elif self.video_service_user:
            return 'User: %s: %s' % (
                self.video_service(),
                self.video_service_user)
        else:
            return ''

    def submitter(self):
        """
        Return the user that submitted this video.  If necessary, use the
        submitter from the originating feed or savedsearch.
        """
        if self.user is not None:
            return self.user
        elif self.feed is not None:
            return self.feed.user
        elif self.search is not None:
            return self.search.user
        else:
            # XXX warning?
            return None

    def when(self):
        """
        Simple method for getting the when_published date if the video came
        from a feed or a search, otherwise the when_approved date.
        """
        if SiteLocation.objects.get(site=self.site_id).use_original_date and \
                self.when_published:
            return self.when_published
        return self.when_approved or self.when_submitted

    def when_prefix(self):
        """
        When videos are bulk imported (from a feed or a search), we list the
        date as "published", otherwise we show 'posted'.
        """

        if self.when_published and \
                SiteLocation.objects.get(site=self.site_id).use_original_date:
            return 'published'
        else:
            return 'posted'

    def video_service(self):
        if not self.website_url:
            return

        url = self.website_url
        for service, regexp in VIDEO_SERVICE_REGEXES:
            if re.search(regexp, url, re.I):
                return service


class VideoAdmin(admin.ModelAdmin):
    list_display = ('name', 'site', 'when_submitted', 'status', 'feed')
    list_filter = ['status', 'when_submitted']
    search_fields = ['name', 'description']


class Watch(models.Model):
    """
    Record of a video being watched.

    fields:
     - video: Video that was watched
     - timestamp: when watched
     - user: user that watched it, if any
     - ip_address: IP address of the user
    """
    video = models.ForeignKey(Video)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('auth.User', blank=True, null=True)
    ip_address = models.IPAddressField()

    @classmethod
    def add(Class, request, video):
        """
        Adds a record of a watched video to the database.  If the request came
        from localhost, check to see if it was forwarded to (hopefully) get the
        right IP address.
        """
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        if not ipv4_re.match(ip):
            ip = '0.0.0.0'

        if hasattr(request, 'user') and request.user.is_authenticated():
            user = request.user
        else:
            user = None

        try:
            Class(video=video, user=user, ip_address=ip).save()
        except Exception:
            pass


class VideoModerator(CommentModerator):

    def allow(self, comment, video, request):
        sitelocation = SiteLocation.objects.get(site=video.site)
        if sitelocation.comments_required_login:
            return request.user and request.user.is_authenticated()
        else:
            return True

    def email(self, comment, video, request):
        # we do the import in the function because otherwise there's a circular
        # dependency
        from localtv.util import send_notice

        sitelocation = SiteLocation.objects.get(site=video.site)
        t = loader.get_template('comments/comment_notification_email.txt')
        c = Context({ 'comment': comment,
                      'content_object': video,
                      'user_is_admin': True})
        subject = '[%s] New comment posted on "%s"' % (video.site.name,
                                                       video)
        message = t.render(c)
        send_notice('admin_new_comment', subject, message,
                    sitelocation=sitelocation)

        if video.user and video.user.email:
            video_comment = notification.NoticeType.objects.get(
                label="video_comment")
            admin_new_comment = notification.NoticeType.objects.get(
                label="admin_new_comment")
            if notification.should_send(video.user, video_comment, "1") and \
               not notification.should_send(video.user,
                                            admin_new_comment, "1"):
               c = Context({ 'comment': comment,
                             'content_object': video,
                             'user_is_admin': False})
               message = t.render(c)
               EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL,
                            [video.user.email]).send(fail_silently=True)

    def moderate(self, comment, video, request):
        sitelocation = SiteLocation.objects.get(site=video.site)
        if sitelocation.screen_all_comments:
            if not getattr(request, 'user'):
                return True
            else:
                return not sitelocation.user_is_admin(request.user)
        else:
            return False


moderator.register(Video, VideoModerator)

admin.site.register(SiteLocation)
admin.site.register(Feed)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Video, VideoAdmin)
admin.site.register(SavedSearch)
admin.site.register(Watch)

tagging.register(Video)

def finished(sender, **kwargs):
    SiteLocation.objects.clear_cache()
request_finished.connect(finished)

def tag_unicode(self):
    # hack to make sure that Unicode data gets returned for all tags
    if isinstance(self.name, str):
        self.name = self.name.decode('utf8')
    return self.name

tagging.models.Tag.__unicode__ = tag_unicode

submit_finished = django.dispatch.Signal()

def send_new_video_email(sender, **kwargs):
    sitelocation = SiteLocation.objects.get(site=sender.site)
    if sender.status == VIDEO_STATUS_ACTIVE:
        # don't send the e-mail for new videos
        return
    t = loader.get_template('localtv/submit_video/new_video_email.txt')
    c = Context({'video': sender})
    message = t.render(c)
    subject = '[%s] New Video in Review Queue: %s' % (sender.site.name,
                                                          sender)
    util.send_notice('admin_new_submission',
                     subject, message,
                     sitelocation=sitelocation)

submit_finished.connect(send_new_video_email, weak=False)


def create_email_notices(app, created_models, verbosity, **kwargs):
    notification.create_notice_type('video_comment',
                                    'New comment on your video',
                                    'Someone commented on your video',
                                    default=2,
                                    verbosity=verbosity)
    notification.create_notice_type('video_approved',
                                    'Your video was approved',
                                    'An admin approved your video',
                                    default=2,
                                    verbosity=verbosity)
    notification.create_notice_type('admin_new_comment',
                                    'New comment',
                                    'A comment was submitted to the site',
                                    default=1,
                                    verbosity=verbosity)
    notification.create_notice_type('admin_new_submission',
                                    'New Submission',
                                    'A new video was submitted',
                                    default=1,
                                    verbosity=verbosity)
    notification.create_notice_type('admin_queue_weekly',
                                        'Weekly Queue Update',
                                    'A weekly e-mail of the queue status',
                                    default=1,
                                    verbosity=verbosity)
    notification.create_notice_type('admin_queue_daily',
                                    'Daily Queue Update',
                                    'A daily e-mail of the queue status',
                                    default=1,
                                    verbosity=verbosity)

models.signals.post_syncdb.connect(create_email_notices,
                                   sender=notification)

