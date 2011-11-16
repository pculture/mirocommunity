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
import email.utils
import httplib
import re
import urllib
import urllib2
import mimetypes
import base64
import os
import logging

try:
    from PIL import Image
except ImportError:
    import Image
import time
from BeautifulSoup import BeautifulSoup

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.moderation import CommentModerator, moderator
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.core.signals import request_finished
import django.dispatch
from django.core.validators import ipv4_re
from django.template import Context, loader
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
import django.utils.html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

import bitly
import vidscraper

from notification import models as notification
import tagging

from localtv.exceptions import InvalidVideo, CannotOpenImageUrl
from localtv.templatetags.filters import sanitize
from localtv import utils
from localtv.signals import post_video_from_vidscraper
import localtv.tiers

def delete_if_exists(path):
    if default_storage.exists(path):
        default_storage.delete(path)

EMPTY = object()

UNAPPROVED_STATUS_TEXT = _(u'Unapproved')
ACTIVE_STATUS_TEXT = _(u'Active')
REJECTED_STATUS_TEXT = _(u'Rejected')
PENDING_THUMBNAIL_STATUS_TEXT = _(u'Waiting on thumbnail')
DISABLED_STATUS_TEXT = _(u'Disabled')

THUMB_SIZES = [ # for backwards, compatibility; it's now a class variable
    (534, 430), # behind a video
    (375, 295), # featured on frontpage
    (140, 110),
    (364, 271), # main thumb
    (222, 169), # medium thumb
    (88, 68),   # small thumb
    ]

FORCE_HEIGHT_CROP = 1 # arguments for thumbnail resizing
FORCE_HEIGHT_PADDING = 2

VIDEO_SERVICE_REGEXES = (
    ('YouTube', r'http://gdata\.youtube\.com/feeds/'),
    ('YouTube', r'http://(www\.)?youtube\.com/'),
    ('blip.tv', r'http://(.+\.)?blip\.tv/'),
    ('Vimeo', r'http://(www\.)?vimeo\.com/'),
    ('Dailymotion', r'http://(www\.)?dailymotion\.com/rss'))


POPULAR_QUERY_TIMEOUT = getattr(settings, 'LOCALTV_POPULAR_QUERY_TIMEOUT',
                                120 * 60) # 120 minutes


class BitLyWrappingURLField(models.URLField):
    def get_db_prep_value(self, value, *args, **kwargs):
        if not getattr(settings, 'BITLY_LOGIN'):
            return value

        # Workaround for some cases
        if value is None:
            value = ''

        if len(value) <= self.max_length: # short enough to save
            return value
        api = bitly.Api(login=settings.BITLY_LOGIN,
                        apikey=settings.BITLY_API_KEY)
        try:
            return unicode(api.shorten(value))
        except bitly.BitlyError:
            return unicode(value)[:self.max_length]


from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^localtv\.models\.BitLyWrappingURLField"])


class Thumbnailable(models.Model):
    """
    A type of Model that has thumbnails generated for it.
    """
    has_thumbnail = models.BooleanField(default=False)
    thumbnail_extension = models.CharField(max_length=8, blank=True)

    class Meta:
        abstract = True

    def save_thumbnail_from_file(self, content_thumb, resize=True):
        """
        Takes an image file-like object and stores it as the thumbnail for this
        video item.
        """
        try:
            pil_image = Image.open(content_thumb)
        except IOError:
            raise CannotOpenImageUrl('An image could not be loaded')

        # save an unresized version, overwriting if necessary
        delete_if_exists(
            self.get_original_thumb_storage_path())

        self.thumbnail_extension = pil_image.format.lower()
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

        if resize:
            # save any resized versions
            self.resize_thumbnail(pil_image)
        self.has_thumbnail = True
        self.save()

    def resize_thumbnail(self, thumb, resized_images=None):
        """
        Creates resized versions of the video's thumbnail image
        """
        if not thumb:
            thumb = Image.open(
                default_storage.open(self.get_original_thumb_storage_path()))
        if resized_images is None:
            resized_images = localtv.utils.resize_image_returning_list_of_strings(
                thumb, self.THUMB_SIZES)
        for ( (width, height), data) in resized_images:
            # write file, deleting old thumb if it exists
            cf_image = ContentFile(data)
            delete_if_exists(
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
        delete_if_exists(self.get_original_thumb_storage_path())
        for size in self.THUMB_SIZES:
            delete_if_exists(
                self.get_resized_thumb_storage_path(*size[:2]))
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
            # Dig it out of the cache.
            current_site_location = SITE_LOCATION_CACHE[sid]
        except KeyError:
            # Not in the cache? Time to put it in the cache.
            try:
                # If it is in the DB, get it.
                current_site_location = self.select_related().get(site__pk=sid)
            except SiteLocation.DoesNotExist:
                # Otherwise, create it.
                current_site_location = localtv.models.SiteLocation.objects.create(
                    site=Site.objects.get_current())

            SITE_LOCATION_CACHE[sid] = current_site_location
        return current_site_location

    def get(self, **kwargs):
        if 'site' in kwargs:
            site = kwargs['site']
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


class SingletonManager(models.Manager):
    def get_current(self):
        current_site_location = SiteLocation._default_manager.db_manager(
            self.db).get_current()
        singleton, created = self.get_or_create(
            sitelocation = current_site_location)
        if created:
            logging.info("Created %s." % self.model.__class__.__name__)
        return singleton


class TierInfo(models.Model):
    payment_due_date = models.DateTimeField(null=True, blank=True)
    free_trial_available = models.BooleanField(default=True)
    free_trial_started_on = models.DateTimeField(null=True, blank=True)
    in_free_trial = models.BooleanField(default=False)
    payment_secret = models.CharField(max_length=255, default='',blank=True) # This is part of payment URLs.
    current_paypal_profile_id = models.CharField(max_length=255, default='',blank=True) # NOTE: When using this, fill it if it seems blank.
    video_allotment_warning_sent = models.BooleanField(default=False)
    free_trial_warning_sent = models.BooleanField(default=False)
    already_sent_welcome_email = models.BooleanField(default=False)
    inactive_site_warning_sent = models.BooleanField(default=False)
    user_has_successfully_performed_a_paypal_transaction = models.BooleanField(default=False)
    already_sent_tiers_compliance_email = models.BooleanField(default=False)
    fully_confirmed_tier_name = models.CharField(max_length=255, default='', blank=True)
    should_send_welcome_email_on_paypal_event = models.BooleanField(default=False)
    waiting_on_payment_until = models.DateTimeField(null=True, blank=True)
    sitelocation = models.OneToOneField('SiteLocation')
    objects = SingletonManager()

    def get_payment_secret(self):
        '''The secret had better be non-empty. So we make it non-empty right here.'''
        if self.payment_secret:
            return self.payment_secret
        # Guess we had better fill it.
        self.payment_secret = base64.b64encode(os.urandom(16))
        self.save()
        return self.payment_secret

    def site_is_subsidized(self):
        return (self.current_paypal_profile_id == 'subsidized')

    def set_to_subsidized(self):
        if self.current_paypal_profile_id:
            raise AssertionError, (
                "Bailing out: " +
                "the site already has a payment profile configured: %s" %
                                   self.current_paypal_profile_id)
        self.current_paypal_profile_id = 'subsidized'

    def time_until_free_trial_expires(self, now = None):
        if not self.in_free_trial:
            return None
        if not self.payment_due_date:
            return None

        if now is None:
            now = datetime.datetime.utcnow()
        return (self.payment_due_date - now)

    def use_zendesk(self):
        '''If the site is configured to, we can send notifications of
        tiers-related changes to ZenDesk, the customer support ticketing
        system used by PCF.

        A non-PCF deployment of localtv would not want to set the
        LOCALTV_USE_ZENDESK setting. Then this method will return False,
        and the parts of the tiers system that check it will avoid
        making calls out to ZenDesk.'''
        return getattr(settings, 'LOCALTV_USE_ZENDESK', False)


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
     - status: one of SiteLocation.STATUS_CHOICES
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
     - tier_name: A short string representing the class of site. This relates to paid extras.
    """
    DISABLED = 0
    ACTIVE = 1

    STATUS_CHOICES = (
        (DISABLED, DISABLED_STATUS_TEXT),
        (ACTIVE, ACTIVE_STATUS_TEXT),
    )

    site = models.ForeignKey(Site, unique=True)
    logo = models.ImageField(upload_to='localtv/site_logos', blank=True)
    background = models.ImageField(upload_to='localtv/site_backgrounds',
                                   blank=True)
    admins = models.ManyToManyField('auth.User', blank=True,
                                    related_name='admin_for')
    status = models.IntegerField(
        choices=STATUS_CHOICES, default=ACTIVE)
    sidebar_html = models.TextField(blank=True)
    footer_html = models.TextField(blank=True)
    about_html = models.TextField(blank=True)
    tagline = models.CharField(max_length=4096, blank=True)
    css = models.TextField(blank=True)
    display_submit_button = models.BooleanField(default=True)
    submission_requires_login = models.BooleanField(default=False)
    playlists_enabled = models.IntegerField(default=1)
    tier_name = models.CharField(max_length=255, default='basic', blank=False, choices=localtv.tiers.CHOICES)
    hide_get_started = models.BooleanField(default=False)

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

    THUMB_SIZES = [
        (88, 68, False),
        (140, 110, False),
        (222, 169, False),
        (130, 110, FORCE_HEIGHT_PADDING) # Facebook
        ]

    def __unicode__(self):
        return '%s (%s)' % (self.site.name, self.site.domain)

    def add_queued_mail(self, data):
        if not hasattr(self, '_queued_mail'):
            self._queued_mail = []
        self._queued_mail.append(data)

    def get_queued_mail_destructively(self):
        ret = getattr(self, '_queued_mail', [])
        self._queued_mail = []
        return ret

    @staticmethod
    def enforce_tiers(override_setting=None, using='default'):
        '''If the admin has set LOCALTV_DISABLE_TIERS_ENFORCEMENT to a True value,
        then this function returns False. Otherwise, it returns True.'''
        if override_setting is None:
            disabled = getattr(settings, 'LOCALTV_DISABLE_TIERS_ENFORCEMENT', False)
        else:
            disabled = override_setting

        if disabled:
            # Well, hmm. If the site admin participated in a PayPal transaction, then we
            # actually will enforce the tiers.
            #
            # Go figure.
            tierdata = TierInfo.objects.db_manager(using).get_current()
            if tierdata.user_has_successfully_performed_a_paypal_transaction:
                return True # enforce it.

        # Generally, we just negate the "disabled" boolean.
        return not disabled

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
        SITE_LOCATION_CACHE[self.site_id] = self
        return models.Model.save(self, *args, **kwargs)

    def get_tier(self):
        return localtv.tiers.Tier(self.tier_name, self)

    def get_fully_confirmed_tier(self):
        # If we are in a transitional state, then we would have stored
        # the last fully confirmed tier name in an unusual column.
        tierdata = TierInfo.objects.get_current()
        if tierdata.fully_confirmed_tier_name:
            return localtv.tiers.Tier(tierdata.fully_confirmed_tier_name)
        return None

    def get_css_for_display_if_permitted(self):
        '''This function checks the site tier, and if permitted, returns the
        custom CSS the admin has set.

        If that is not permitted, it returns the empty unicode string.'''
        if (not self.enforce_tiers() or
            self.get_tier().permit_custom_css()):
            # Sweet.
            return self.css
        else:
            # Silenced.
            return u''

    def should_show_dashboard(self):
        '''On /admin/, most sites will see a dashboard that gives them
        information at a glance about the site, including its tier status.

        Some sites want to disable that, which they can do by setting the
        LOCALTV_SHOW_ADMIN_DASHBOARD variable to False.

        In that case (in the default theme) the left-hand navigation
        will omit the link to the Dashboard, and also the dashboard itself
        will be an empty page with a META REFRESH that points to
        /admin/approve_reject/.'''
        return getattr(settings, 'LOCALTV_SHOW_ADMIN_DASHBOARD', True)

    def should_show_account_level(self):
        '''On /admin/upgrade/, most sites will see an info page that
        shows how to change their account level (AKA site tier).

        Some sites want to disable that, which they can do by setting the
        LOCALTV_SHOW_ADMIN_ACCOUNT_LEVEL variable to False.

        This simply removes the link from the sidebar; if you visit the
        /admin/upgrade/ page, it renders as usual.'''
        return getattr(settings, 'LOCALTV_SHOW_ADMIN_ACCOUNT_LEVEL', True)


class NewsletterSettings(models.Model):
    DISABLED = 0
    FEATURED = 1
    POPULAR = 2
    CUSTOM = 3
    LATEST = 4
    
    STATUS_CHOICES = (
        (DISABLED, DISABLED_STATUS_TEXT),
        (FEATURED, _("5 most recently featured")),
        (POPULAR, _("5 most popular")),
        (LATEST, _("5 latest videos")),
        (CUSTOM, _("Custom selection")),
    )
    sitelocation = models.OneToOneField(SiteLocation)
    status = models.IntegerField(
        choices=STATUS_CHOICES, default=DISABLED,
        help_text='What videos should get sent out in the newsletter?')

    # for custom newsletter
    video1 = models.ForeignKey('Video', related_name='newsletter1', null=True,
                               help_text='A URL of a video on your site.')
    video2 = models.ForeignKey('Video', related_name='newsletter2', null=True,
                               help_text='A URL of a video on your site.')
    video3 = models.ForeignKey('Video', related_name='newsletter3', null=True,
                               help_text='A URL of a video on your site.')
    video4 = models.ForeignKey('Video', related_name='newsletter4', null=True,
                               help_text='A URL of a video on your site.')
    video5 = models.ForeignKey('Video', related_name='newsletter5', null=True,
                               help_text='A URL of a video on your site.')
    
    intro = models.CharField(max_length=200, blank=True,
                             help_text=('Include a short introduction to your '
                                        'newsletter. If you will be sending '
                                        'the newsletter automatically, make '
                                        'sure to update this or write '
                                        'something that will be evergreen! '
                                        '(limit 200 characters)'))
    show_icon = models.BooleanField(default=True,
                                    help_text=('Do you want to include your '
                                               'site logo in the newsletter '
                                               'header?'))

    twitter_url = models.URLField(verify_exists=False, blank=True,
                                  help_text='e.g. https://twitter.com/#!/mirocommunity')
    facebook_url = models.URLField(verify_exists=False, blank=True,
                                   help_text='e.g. http://www.facebook.com/universalsubtitles')

    repeat = models.IntegerField(default=0) # hours between sending
    last_sent = models.DateTimeField(null=True)

    objects = SingletonManager()

    def videos(self):
        if self.status == NewsletterSettings.DISABLED:
            raise ValueError('no videos for disabled newsletter')
        elif self.status == NewsletterSettings.FEATURED:
            videos = Video.objects.get_featured_videos(self.sitelocation)
        elif self.status == NewsletterSettings.POPULAR:
            # popular over the last week
            videos = Video.objects.get_popular_videos(self.sitelocation)
        elif self.status == NewsletterSettings.LATEST:
            videos = Video.objects.get_latest_videos(self.sitelocation)
        elif self.status == NewsletterSettings.CUSTOM:
            videos = [video for video in (
                    self.video1,
                    self.video2,
                    self.video3,
                    self.video4,
                    self.video5) if video]
        return videos[:5]

    def next_send_time(self):
        if not self.repeat:
            return None
        if not self.last_sent:
            dt = datetime.datetime.now()
        else:
            dt = self.last_sent
        return dt + datetime.timedelta(hours=self.repeat)

    def send(self):
        from localtv.admin.user_views import _filter_just_humans
        body = self.as_html()
        subject = '[%s] Newsletter for %s' % (self.sitelocation.site.name,
                                              datetime.datetime.now().strftime('%m/%d/%y'))
        notice_type = notification.NoticeType.objects.get(label='newsletter')
        for u in User.objects.exclude(email=None).exclude(email='').filter(
            _filter_just_humans()):
            if notification.get_notification_setting(u, notice_type, "1"):
                message = EmailMessage(subject, body,
                                       settings.DEFAULT_FROM_EMAIL,
                                       [u.email])
                message.content_subtype = 'html'
                message.send(fail_silently=True)

    def as_html(self, extra_context=None):
        context = {'newsletter': self,
                   'sitelocation': self.sitelocation,
                   'site': self.sitelocation.site}
        if extra_context:
            context.update(extra_context)
        return render_to_string('localtv/admin/newsletter.html',
                                context)


class WidgetSettings(Thumbnailable):
    """
    A Model which represents the options for controlling the widget creator.
    """
    site = models.OneToOneField(Site)

    title = models.CharField(max_length=250, blank=True)
    title_editable = models.BooleanField(default=True)

    icon = models.ImageField(upload_to='localtv/widget_icon', blank=True)
    icon_editable = models.BooleanField(default=False)

    css = models.FileField(upload_to='localtv/widget_css', blank=True)
    css_editable = models.BooleanField(default=False)

    bg_color = models.CharField(max_length=20, blank=True)
    bg_color_editable = models.BooleanField(default=False)

    text_color = models.CharField(max_length=20, blank=True)
    text_color_editable = models.BooleanField(default=False)

    border_color = models.CharField(max_length=20, blank=True)
    border_color_editable = models.BooleanField(default=False)

    THUMB_SIZES = [
        (88, 68, False),
        (140, 110, False),
        (222, 169, False),
        ]

    def get_title_or_reasonable_default(self):
        # Is the title worth using? If so, use that.
        use_title = True
        if self.title.endswith('example.com'):
            use_title = False
        if not self.title:
            use_title = False

        # Okay, so either we return the title, or a sensible default
        if use_title:
            return django.utils.html.escape(self.title)
        return self.generate_reasonable_default_title()

    def generate_reasonable_default_title(self):
        prefix = 'Watch Videos on %s'

        # Now, work on calculating what goes at the end.
        site = Site.objects.get_current()

        # The default suffix is a self-link. If the site name and
        # site domain are plausible, do that.
        if ((site.name and site.name.lower() != 'example.com') and
            (site.domain and site.domain.lower() != 'example.com')):
            suffix = '<a href="http://%s/">%s</a>' % (
                site.domain, django.utils.html.escape(site.name))

        # First, we try the site name, if that's a nice string.
        elif site.name and site.name.lower() != 'example.com':
            suffix = site.name

        # Else, we try the site domain, if that's not example.com
        elif site.domain.lower() != 'example.com':
            suffix = site.domain

        else:
            suffix = 'our video site'

        return prefix % suffix


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

    THUMB_SIZES = THUMB_SIZES

    class Meta:
        abstract = True

    def _default_video_status(self):
        # Check that if we want to add an active
        sl = SiteLocation.objects.using(self._state.db).get(site=self.site)
        if self.auto_approve and sl.get_tier().can_add_more_videos():
            initial_video_status = Video.ACTIVE
        else:
            initial_video_status = Video.UNAPPROVED
        return initial_video_status

    def bulk_import(self, videos, verbose=False, clear_rejected=True,
                    actually_save_thumbnails=True, **kwargs):
        """
        Imports videos from a feed/search.  `videos` is an iterable which
        returns :class:`vidscraper.suites.base.Video` objects.  We use
        :method:`.Video.from_vidscraper_video to map the Vidscraper fields to
        Video attributes.
        """
        def skip(video, reason, *args):
            m = "Skipping %r: %s" % (video.title, reason % args)
            logging.debug(m)
            if True: #verbose:
                print m

        if 'status' not in kwargs:
            kwargs['status'] = self._default_video_status()

        if 'site' not in kwargs:
            kwargs['site'] = self.site

        if 'authors' not in kwargs:
            kwargs['authors'] = list(self.auto_authors.all())
        if 'categories' not in kwargs:
            kwargs['categories'] = list(self.auto_categories.all())

        #guids = set(self.video_set.values_list('guid', 'when_published'))
        if verbose:
            print 'Starting video iterator'

        from localtv.tasks import video_from_vidscraper_video

        for vidscraper_video in iter(videos):
            if not vidscraper_video.title:
                skip(vidscraper_video, 'failed to scrape basic data')
                continue
            # elif (vidscraper_video.guid and
            #       (vidscraper_video.guid,
            #        vidscraper_video.publish_datetime) in guids):
            #     skip(vidscraper_video, 'duplicate guid')
            #     continue
            # elif vidscraper_video.link:
            #     videos_with_link = Video.objects.using(self._state.db).filter(
                    
            #         website_url=vidscraper_video.link)
            #     if clear_rejected:
            #         videos_with_link.rejected().delete()
            #     if videos_with_link.filter(
            #         when_published=vidscraper_video.publish_datetime).exists():
            #         skip(vidscraper_video, 'duplicate link')
            #         continue
            
            video_from_vidscraper_video.delay(
                vidscraper_video,
                source=self,
                clear_rejected=clear_rejected,
                using=self._state.db,
                **kwargs)
                

class StatusedThumbnailableQuerySet(models.query.QuerySet):

    def unapproved(self):
        return self.filter(status=StatusedThumbnailable.UNAPPROVED)

    def active(self):
        return self.filter(status=StatusedThumbnailable.ACTIVE)

    def rejected(self):
        return self.filter(status=StatusedThumbnailable.REJECTED)

    def pending_thumbnail(self):
        return self.filter(status=StatusedThumbnailable.PENDING_THUMBNAIL)


class StatusedThumbnailableManager(models.Manager):

    def get_query_set(self):
        return StatusedThumbnailableQuerySet(self.model, using=self._db)

    def unapproved(self):
        return self.get_query_set().unapproved()

    def active(self):
        return self.get_query_set().active()

    def rejected(self):
        return self.get_query_set().rejected()

    def pending_thumbnail(self):
        return self.get_query_set().pending_thumbnail()


class StatusedThumbnailable(models.Model):
    """
    Abstract class to provide the ``status`` field for Feeds and Videos.
    """
    #: An admin has not looked at this feed yet.
    UNAPPROVED = 0
    ACTIVE = 1
    #: This feed was rejected by an admin.
    REJECTED = 2
    PENDING_THUMBNAIL = 3

    STATUS_CHOICES = (
        (UNAPPROVED, UNAPPROVED_STATUS_TEXT),
        (ACTIVE, ACTIVE_STATUS_TEXT),
        (REJECTED, REJECTED_STATUS_TEXT),
        (PENDING_THUMBNAIL, PENDING_THUMBNAIL_STATUS_TEXT),
    )

    objects = StatusedThumbnailableManager()

    status = models.IntegerField(
        choices=STATUS_CHOICES, default=UNAPPROVED)

    def is_active(self):
        """Shortcut to check the common case of whether a video is active."""
        return self.status == self.ACTIVE

    class Meta:
        abstract = True


class Feed(Source, StatusedThumbnailable):
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
      - status: one of Feed.STATUS_CHOICES
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
    etag = models.CharField(max_length=250, blank=True)
    avoid_frontpage = models.BooleanField(default=False)
    calculated_source_type = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        unique_together = (
            ('feed_url', 'site'))
        get_latest_by = 'last_updated'

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_list_feed', [self.pk])

    def update_items(self, verbose=False, clear_rejected=False, video_iter=None):
        """
        Fetch and import new videos from this feed.

        If clear_rejected is True, rejected videos that are part of this
        feed will be deleted and re-imported.
        """
        feedimport, created = FeedImport.objects.db_manager(
            self._state.db).get_or_create(feed=self, end=None)
        if not created:
            if verbose:
                print 'Skipping import of %s: already in progress' % self
            return
        if video_iter is None:
            video_iter = vidscraper.auto_feed(
                self.feed_url,
                fields=['title', 'file_url', 'embed_code', 'flash_enclosure_url',
                        'publish_datetime', 'thumbnail_url', 'link',
                        'file_url_is_flaky', 'user', 'user_url',
                        'tags', 'description', 'file_url', 'guid'])
        try:
            video_iter.load()
            self.bulk_import(video_iter,
                             feed=self,
                             feedimport=feedimport,
                             verbose=verbose)

            self.etag = getattr(video_iter, 'etag', None) or ''
            self.last_updated = (getattr(video_iter, 'last_modified', None) or
                                 datetime.datetime.now())
            self.save()
        finally:
            feedimport.end = datetime.datetime.now()
            feedimport.save()

    def source_type(self):
        return self.calculated_source_type

    def _calculate_source_type(self):
        return _feed__calculate_source_type(self)

    def video_service(self):
        return feed__video_service(self)

def feed__video_service(feed):
    # This implements the video_service method. It's outside the Feed class
    # so we can use it safely from South.
    for service, regexp in VIDEO_SERVICE_REGEXES:
        if re.search(regexp, feed.feed_url, re.I):
            return service

def _feed__calculate_source_type(feed):
    # This implements the _calculate_source_type method. It's outside the Feed
    # class so we can use it safely from South.
    video_service = feed__video_service(feed)
    if video_service is None:
        return u'Feed'
    else:
        return u'User: %s' % video_service

def pre_save_set_calculated_source_type(instance, **kwargs):
    # Always save the calculated_source_type
    instance.calculated_source_type = _feed__calculate_source_type(instance)
    # Plus, if the name changed, we have to recalculate all the Videos that depend on us.
    try:
        v = Feed.objects.using(instance._state.db).get(id=instance.id)
    except Feed.DoesNotExist:
        return instance
    if v.name != instance.name:
        # recalculate all the sad little videos' calculated_source_type
        for vid in instance.video_set.all():
            vid.save()
    return instance
models.signals.pre_save.connect(pre_save_set_calculated_source_type,
                                sender=Feed)

class FeedImportIndex(models.Model):
    feedimport = models.ForeignKey('FeedImport')
    video = models.OneToOneField('Video')
    index = models.IntegerField()

class FeedImport(models.Model):
    feed = models.ForeignKey(Feed)
    start = models.DateTimeField(auto_now_add=True)
    end = models.DateTimeField(null=True)

    class Meta:
        get_latest_by = 'start'

    @property
    def video_set(self):
        return Video.objects.filter(feedimportindex__feedimport=self)

class Category(models.Model):
    """
    A category for videos to be contained in.

    Categories and tags aren't too different functionally, but categories are
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

    # only relevant is voting is enabled for the site
    contest_mode = models.DateTimeField('Turn on Contest',
                                        null=True,
                                        default=None)

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
        """
        Returns active videos for the category and its subcategories, ordered
        by decreasing best date.
        
        """
        categories = [self] + self.in_order(self.site, self.child_set.all())
        return Video.objects.active().filter(
            categories__in=categories).distinct()
    approved_set = property(approved_set)

    def unique_error_message(self, model_class, unique_check):
        return 'Category with this %s already exists.' % (
            unique_check[0],)

    def has_votes(self):
        """
        Returns True if this category has videos with votes.
        """
        if not localtv.settings.voting_enabled():
            return False
        import voting
        return voting.models.Vote.objects.filter(
            content_type=ContentType.objects.get_for_model(Video),
            object_id__in=self.approved_set.values_list('id',
                                                        flat=True)).exists()


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

    def update_items(self, verbose=False, video_iter=None):
        if video_iter is None:
            searches = vidscraper.auto_search(
                self.query_string,
                fields=['title', 'file_url', 'embed_code',
                        'flash_enclosure_url', 'publish_datetime',
                        'thumbnail_url', 'link', 'file_url_is_flaky', 'user',
                        'user_url', 'tags', 'description', 'file_url', 'guid'])
            def video_gen():
                for suite in searches.values():
                    for video in iter(suite):
                        yield video
            video_iter = video_gen()

        self.bulk_import(video_iter, search=self,
                         verbose=verbose)

    def source_type(self):
        return u'Search'


class VideoBase(models.Model):
    """
    Base class between Video and OriginalVideo.  It would be simple enough to
    duplicate these fields, but this way it's easier to add more points of
    duplication in the future.
    """
    name = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    thumbnail_url = models.URLField(
        verify_exists=False, blank=True, max_length=400)

    class Meta:
        abstract = True

class OriginalVideo(VideoBase):

    VIDEO_ACTIVE, VIDEO_DELETED, VIDEO_DELETE_PENDING = range(3)

    video = models.OneToOneField('Video', related_name='original')
    thumbnail_updated = models.DateTimeField(blank=True)
    remote_video_was_deleted = models.IntegerField(default=VIDEO_ACTIVE)
    remote_thumbnail_hash = models.CharField(max_length=64, default='')

    def changed_fields(self, override_vidscraper_result=None):
        """
        Check our video for new data.
        """
        video = self.video
        if not video.website_url:
            # we shouldn't have been created, but either way we can't do
            # anything here
            self.delete()
            return {}

        remote_video_was_deleted = False
        fields = ['title', 'description', 'tags', 'thumbnail_url']
        if override_vidscraper_result is not None:
            vidscraper_video = override_vidscraper_result
        else:
            try:
                vidscraper_video = vidscraper.auto_scrape(
                    video.website_url, fields=fields)
            except vidscraper.errors.VideoDeleted:
                remote_video_was_deleted = True

        # Now that we have the "scraped_data", analyze it: does it look like
        # a skeletal video, with no data? Then we infer it was deleted.
        if remote_video_was_deleted or all(not getattr(vidscraper_video, field)
                                           for field in fields):
            remote_video_was_deleted = True
        # If the scraped_data has all None values, then infer that the remote video was
        # deleted.

        if remote_video_was_deleted:
            if self.remote_video_was_deleted == OriginalVideo.VIDEO_DELETED:
                return {} # We already notified the admins of the deletion.
            else:
                return {'deleted': True}
        elif self.remote_video_was_deleted:
            return {'deleted': False}

        changed_fields = {}

        for field in fields:
            if field == 'tags': # special case tag checking
                if vidscraper_video.tags is None:
                    # failed to get tags, so don't send a spurious change
                    # message
                    continue
                new = utils.unicode_set(vidscraper_video.tags)
                if getattr(settings, 'FORCE_LOWERCASE_TAGS'):
                    new = utils.unicode_set(name.lower() for name in new)
                old = utils.unicode_set(self.tags)
                if new != old:
                    changed_fields[field] = new
            elif field == 'thumbnail_url':
                if vidscraper_video.thumbnail_url != self.thumbnail_url:
                    changed_fields[field] = vidscraper_video.thumbnail_url
                else:
                    right_now = datetime.datetime.utcnow()
                    if self._remote_thumbnail_appears_changed():
                        changed_fields['thumbnail_updated'] = right_now
            else:
                if field == 'title':
                    model_field = 'name'
                else:
                    model_field = field
                if (utils.normalize_newlines(
                        getattr(vidscraper_video, field)) !=
                    utils.normalize_newlines(
                        getattr(self, model_field))):
                    changed_fields[model_field] = getattr(vidscraper_video, field)

        return changed_fields

    def originals_for_changed_fields(self, changed_fields):
        '''The OriginalVideo emails need to say not just the new data, but also
        provide the value that was in the OriginalVideo object just before the
        email is sent.

        This function takes a changed_fields dictionary, and uses its keys to
        figure out what relevant snapshotted information would help the user
        contextualize the changed_fields data.'''
        old_fields = {}

        if 'deleted' in changed_fields:
            return old_fields

        for key in changed_fields:
            old_fields[key] = getattr(self, key)

        return old_fields

    def _remote_thumbnail_appears_changed(self):
        '''This private method checks if the remote thumbnail has been updated.

        It takes no arguments, because you are only supposed to call it
        when the remote video service did not give us a new thumbnail URL.

        It returns a boolean. True, if and only if the remote video has:

        * a Last-Modified header indicating it has been modified, and
        * HTTP response body that hashes to a different SHA1 than the
          one we stored.

        It treats "self" as read-only.'''
        # because the data might have changed, check to see if the
        # thumbnail has been modified
        made_time = time.mktime(self.thumbnail_updated.utctimetuple())
        # we take made_time literally, because the localtv app MUST
        # be storing UTC time data in the column.
        modified = email.utils.formatdate(made_time,
                                          usegmt=True)
        request = urllib2.Request(self.thumbnail_url)
        request.add_header('If-Modified-Since', modified)
        try:
            response = urllib2.build_opener().open(request)
        except urllib2.HTTPError:
            # We get this for 304, but we'll just ignore all the other
            # errors too
            return False
        else:
            if response.info().get('Last-modified', modified) == \
                    modified:
                # hasn't really changed, or doesn't exist
                return False

        # If we get here, then the remote server thinks that the file is fresh.
        # We should check its SHA1 hash against the one we have stored.
        new_sha1 = utils.hash_file_obj(response)

        if new_sha1 == self.remote_thumbnail_hash:
            # FIXME: Somehow alert downstream layers that it is safe to update
            # the modified-date in the database.
            return False # bail out early, empty -- the image is the same

        # Okay, so the hashes do not match; the remote image truly has changed.
        # Let's report the timestamp as having a Last-Modified date of right now.
        return True

    def send_deleted_notification(self):
        if self.remote_video_was_deleted == OriginalVideo.VIDEO_DELETE_PENDING:
            from localtv.utils import send_notice
            t = loader.get_template('localtv/admin/video_deleted.txt')
            c = Context({'video': self.video})
            subject = '[%s] Video Deleted: "%s"' % (
                self.video.site.name, self.video.name)
            message = t.render(c)
            send_notice('admin_video_updated', subject, message,
                        sitelocation=SiteLocation.objects.get(
                    site=self.video.site))
            # Update the OriginalVideo to show that we sent this notification
            # out.
            self.remote_video_was_deleted = OriginalVideo.VIDEO_DELETED
        else:
            # send the message next time
            self.remote_video_was_deleted = OriginalVideo.VIDEO_DELETE_PENDING
        self.save()

    def update(self, override_vidscraper_result = None):
        from localtv.utils import get_or_create_tags

        changed_fields = self.changed_fields(override_vidscraper_result)
        if not changed_fields:
            return # don't need to do anything

        # Was the remote video deleted?
        if changed_fields.pop('deleted', None):
            # Have we already sent the notification
            # Mark inside the OriginalVideo that the video has been deleted.
            # Yes? Uh oh.
            self.send_deleted_notification()
            return # Stop processing here.

        original_values = self.originals_for_changed_fields(changed_fields)

        changed_model = False
        for field in changed_fields.copy():
            if field == 'tags': # special case tag equality
                if set(self.tags) == set(self.video.tags):
                    self.tags = self.video.tags = get_or_create_tags(
                        changed_fields.pop('tags'))
            elif field in ('thumbnail_url', 'thumbnail_updated'):
                if self.thumbnail_url == self.video.thumbnail_url:
                    value = changed_fields.pop(field)
                    if field == 'thumbnail_url':
                        self.thumbnail_url = self.video.thumbnail_url = value
                    changed_model = True
                    self.video.save_thumbnail()
            elif getattr(self, field) == getattr(self.video, field):
                value = changed_fields.pop(field)
                setattr(self, field, value)
                setattr(self.video, field, value)
                changed_model = True

        if self.remote_video_was_deleted:
            self.remote_video_was_deleted = OriginalVideo.VIDEO_ACTIVE
            changed_model = True

        if changed_model:
            self.save()
            self.video.save()

        if not changed_fields: # modified them all
            return

        self.send_updated_notification(changed_fields, original_values)

    def send_updated_notification(self, changed_fields, originals_for_changed_fields):
        from localtv.utils import send_notice, get_or_create_tags

        # Create a custom hodge-podge of changed fields and the original values
        hodge_podge = {}
        for key in changed_fields:
            hodge_podge[key] = (
                changed_fields[key],
                originals_for_changed_fields.get(key, None))

        t = loader.get_template('localtv/admin/video_updated.txt')
        c = Context({'video': self.video,
                     'original': self,
                     'changed_fields': hodge_podge})
        subject = '[%s] Video Updated: "%s"' % (
            self.video.site.name, self.video.name)
        message = t.render(c)
        send_notice('admin_video_updated', subject, message,
                    sitelocation=SiteLocation.objects.get(
                site=self.video.site))

        # And update the self instance to reflect the changes.
        for field in changed_fields:
            if field == 'tags':
                self.tags = get_or_create_tags(changed_fields[field])
            else:
                setattr(self, field, changed_fields[field])
        self.save()


class VideoQuerySet(StatusedThumbnailableQuerySet):

    def with_best_date(self, use_original_date=True):
        if use_original_date:
            published = 'localtv_video.when_published,'
        else:
            published = ''
        return self.extra(select={'best_date': """
COALESCE(%slocaltv_video.when_approved,
localtv_video.when_submitted)""" % published})

    def with_watch_count(self, since=EMPTY):
        """
        Returns a QuerySet of videos annotated with a ``watch_count`` of all
        watches since ``since`` (a datetime, which defaults to seven days ago).
        """
        if since is EMPTY:
            since = datetime.datetime.now() - datetime.timedelta(days=7)

        return self.extra(
            select={'watch_count': """SELECT COUNT(*) FROM localtv_watch
WHERE localtv_video.id = localtv_watch.video_id AND
localtv_watch.timestamp > %s"""},
            select_params = (since,)
        )


class VideoManager(StatusedThumbnailableManager):

    def get_query_set(self):
        return VideoQuerySet(self.model, using=self._db)

    def with_best_date(self, *args, **kwargs):
        return self.get_query_set().with_best_date(*args, **kwargs)

    def popular_since(self, *args, **kwargs):
        return self.get_query_set().popular_since(*args, **kwargs)

    def get_sitelocation_videos(self, sitelocation=None):
        """
        Returns a QuerySet of videos which are active and tied to the
        sitelocation. This QuerySet is cached on the request.
        
        """
        if sitelocation is None:
            sitelocation = SiteLocation.objects.get_current()
        return self.active().filter(site=sitelocation.site)

    def get_featured_videos(self, sitelocation=None):
        """
        Returns a ``QuerySet`` of active videos which are considered "featured"
        for the sitelocation.

        """
        return self.get_sitelocation_videos(sitelocation).filter(
            last_featured__isnull=False
        ).order_by(
            '-last_featured',
            '-when_approved',
            '-when_published',
            '-when_submitted'
        )

    def get_latest_videos(self, sitelocation=None):
        """
        Returns a ``QuerySet`` of active videos for the sitelocation, ordered by
        decreasing ``best_date``.
        
        """
        if sitelocation is None:
            sitelocation = SiteLocation.objects.get_current()
        return self.get_sitelocation_videos(sitelocation).with_best_date(
            sitelocation.use_original_date
        ).order_by('-best_date')

    def get_popular_videos(self, sitelocation=None):
        """
        Returns a ``QuerySet`` of active videos considered "popular" for the
        current sitelocation.

        """
        return self.get_latest_videos(sitelocation).with_watch_count().order_by(
            '-watch_count',
            '-best_date'
        )

    def get_category_videos(self, category, sitelocation=None):
        """
        Returns a ``QuerySet`` of active videos considered part of the selected
        category or its descendants for the sitelocation.

        """
        if sitelocation is None:
            sitelocation = SiteLocation.objects.get_current()
        # category.approved_set already checks active().
        return category.approved_set.filter(
            site=sitelocation.site
        ).with_best_date(
            sitelocation.use_original_date
        ).order_by('-best_date')

    def get_tag_videos(self, tag, sitelocation=None):
        """
        Returns a ``QuerySet`` of active videos with the given tag for the
        sitelocation.

        """
        if sitelocation is None:
            sitelocation = SiteLocation.objects.get_current()
        return Video.tagged.with_all(tag).active().filter(
            site=sitelocation.site
        ).order_by(
            '-when_approved',
            '-when_published',
            '-when_submitted'
        )

    def get_author_videos(self, author, sitelocation=None):
        """
        Returns a ``QuerySet`` of active videos published or produced by
        ``author`` related to the sitelocation.

        """
        return self.get_latest_videos(sitelocation).filter(
            models.Q(authors=author) | models.Q(user=author)
        ).distinct().order_by('-best_date')

    def in_feed_order(self, feed=None, sitelocation=None):
        """
        Returns a ``QuerySet`` of active videos ordered by the order they were
        in when originally imported.
        """
        if sitelocation is None and feed:
            sitelocation = SiteLocation.objects.get(site=feed.site)
        if sitelocation:
            qs = self.get_latest_videos(sitelocation)
        else:
            qs = self.all()
        if feed:
            qs = qs.filter(feed=feed)
        return qs.order_by('-feedimportindex__feedimport__start',
                           '-feedimportindex__index',
                           '-id')


class Video(Thumbnailable, VideoBase, StatusedThumbnailable):
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
     - status: one of Video.STATUS_CHOICES
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
    site = models.ForeignKey(Site)
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
    feed = models.ForeignKey(Feed, null=True, blank=True)
    website_url = BitLyWrappingURLField(verbose_name='Website URL',
                                        verify_exists=False,
                                        blank=True)
    embed_code = models.TextField(blank=True)
    flash_enclosure_url = BitLyWrappingURLField(verify_exists=False,
                                                blank=True)
    guid = models.CharField(max_length=250, blank=True)
    user = models.ForeignKey('auth.User', null=True, blank=True)
    search = models.ForeignKey(SavedSearch, null=True, blank=True)
    video_service_user = models.CharField(max_length=250, blank=True,
                                          default='')
    video_service_url = models.URLField(verify_exists=False, blank=True,
                                        default='')
    contact = models.CharField(max_length=250, blank=True,
                               default='')
    notes = models.TextField(blank=True)
    calculated_source_type = models.CharField(max_length=255, blank=True, default='')

    objects = VideoManager()

    THUMB_SIZES = THUMB_SIZES

    class Meta:
        ordering = ['-when_submitted']
        get_latest_by = 'when_modified'

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_view_video', (),
                {'video_id': self.id,
                 'slug': slugify(self.name)[:30]})

    @classmethod
    def from_vidscraper_video(cls, video, status=None, commit=True, using='default', **kwargs):
        """
        Builds a :class:`Video` instance from a
        :class:`vidscraper.suites.base.Video` instance. If `commit` is False,
        the :class:`Video` will not be saved.  There will be a `save_m2m()`
        method that must be called after you call `save()`.

        """
        if not video.embed_code and not video.file_url:
            raise InvalidVideo

        if status is None:
            status = cls.UNAPPROVED
        if 'site' not in kwargs:
            kwargs['site'] = Site.objects.get_current()

        authors = kwargs.pop('authors', None)
        categories = kwargs.pop('categories', None)
        feedimport = kwargs.pop('feedimport', None)

        now = datetime.datetime.now()

        instance = cls(
            guid=video.guid or '',
            name=video.title or '',
            description=video.description or '',
            website_url=video.link or '',
            when_published=video.publish_datetime,
            file_url=video.file_url or '',
            file_url_mimetype=video.file_url_mimetype or '',
            file_url_length=video.file_url_length,
            when_submitted=now,
            when_approved=now if status == cls.ACTIVE else None,
            status=status,
            thumbnail_url=video.thumbnail_url or '',
            embed_code=video.embed_code or '',
            flash_enclosure_url=video.flash_enclosure_url or '',
            video_service_user=video.user or '',
            video_service_url=video.user_url or '',
            **kwargs
        )

        if instance.description:
            soup = BeautifulSoup(video.description)
            for tag in soup.findAll(
                'div', {'class': "miro-community-description"}):
                instance.description = tag.renderContents()
                break
            instance.description = sanitize(instance.description,
                                            extra_filters=['img'])

        instance._vidscraper_video = video

        def save_m2m():
            if authors:
                instance.authors = authors
            if categories:
                instance.categories = categories
            if feedimport and video.index is not None:
                FeedImportIndex._default_manager.db_manager(
                    using).create(
                    feedimport=feedimport,
                    video=instance,
                    index=video.index)
            if video.tags:
                tags = set(tag.strip() for tag in video.tags if tag.strip())
                for tag_name in tags:
                    if settings.FORCE_LOWERCASE_TAGS:
                        tag_name = tag_name.lower()
                    tag, created = \
                        tagging.models.Tag._default_manager.db_manager(
                        using).get_or_create(name=tag_name)
                    tagging.models.TaggedItem._default_manager.db_manager(
                        using).create(
                        tag=tag, object=instance)
            post_video_from_vidscraper.send(sender=cls, instance=instance,
                                            vidscraper_video=video)

        if commit:
            instance.save(using=using)
            save_m2m()
        else:
            instance._state.db = using
            instance.save_m2m = save_m2m
        return instance

    def get_tags(self):
        if self.pk is None:
            vidscraper_video = getattr(self, '_vidscraper_video', None)
            return getattr(vidscraper_video, 'tags', None) or []
        return self.tags

    def try_to_get_file_url_data(self):
        """
        Do a HEAD request on self.file_url to find information about
        self.file_url_length and self.file_url_mimetype

        Note that while this method fills in those attributes, it does *NOT*
        run self.save() ... so be sure to do so after calling this method!
        """
        if not self.file_url:
            return

        request = urllib2.Request(utils.quote_unicode_url(self.file_url))
        request.get_method = lambda: 'HEAD'
        try:
            http_file = urllib2.urlopen(request)
        except Exception:
            pass
        else:
            self.file_url_length = http_file.headers.get('content-length')
            self.file_url_mimetype = http_file.headers.get('content-type', '')
            if self.file_url_mimetype in ('application/octet-stream', ''):
                # We got a not-useful MIME type; guess!
                guess = mimetypes.guess_type(self.file_url)
                if guess[0] is not None:
                    self.file_url_mimetype = guess[0]

    def save_thumbnail(self):
        """
        Automatically run the entire file saving process... provided we have a
        thumbnail_url, that is.
        """
        if not self.thumbnail_url:
            return

        try:
            content_thumb = ContentFile(urllib.urlopen(
                    utils.quote_unicode_url(self.thumbnail_url)).read())
        except IOError:
            raise CannotOpenImageUrl('IOError loading %s' % self.thumbnail_url)
        except httplib.InvalidURL:
            # if the URL isn't valid, erase it and move on
            self.thumbnail_url = ''
            self.has_thumbnail = False
            self.save()
        else:
            try:
                self.save_thumbnail_from_file(content_thumb)
            except Exception:
                logging.exception("Error while getting " + repr(self.thumbnail_url))

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
        if SiteLocation.objects.using(self._state.db).get(
            site=self.site_id).use_original_date and \
            self.when_published:
            return self.when_published
        return self.when_approved or self.when_submitted

    def source_type(self):
        return video__source_type(self)

    def video_service(self):
        return video__video_service(self)

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

    def voting_enabled(self):
        if not localtv.settings.voting_enabled():
            return False
        return self.categories.filter(contest_mode__isnull=False).exists()

def video__source_type(self):
    '''This is not a method of the Video so that we can can call it from South.'''
    try:
        if self.search:
            return u'Search: %s' % self.search
        elif self.feed:
            if feed__video_service(self.feed):
                return u'User: %s: %s' % (
                    feed__video_service(self.feed),
                    self.feed.name)
            else:
                return 'Feed: %s' % self.feed.name
        elif self.video_service_user:
            return u'User: %s: %s' % (
                video__video_service(self),
                self.video_service_user)
        else:
            return ''
    except Feed.DoesNotExist:
        return ''

def pre_save_video_set_calculated_source_type(instance, **kwargs):
    # Always recalculate the source_type field.
    instance.calculated_source_type = video__source_type(instance)
    return instance
models.signals.pre_save.connect(pre_save_video_set_calculated_source_type,
                                sender=Video)

def video__video_service(self):
    '''This is not a method of Video so we can call it from a South migration.'''
    if not self.website_url:
        return

    url = self.website_url
    for service, regexp in VIDEO_SERVICE_REGEXES:
        if re.search(regexp, url, re.I):
            return service

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
        from localtv.utils import send_notice

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

        admin_new_comment = notification.NoticeType.objects.get(
            label="admin_new_comment")

        if video.user and video.user.email:
            video_comment = notification.NoticeType.objects.get(
                label="video_comment")
            if notification.should_send(video.user, video_comment, "1") and \
               not notification.should_send(video.user,
                                            admin_new_comment, "1"):
               c = Context({ 'comment': comment,
                             'content_object': video,
                             'user_is_admin': False})
               message = t.render(c)
               EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL,
                            [video.user.email]).send(fail_silently=True)

        comment_post_comment = notification.NoticeType.objects.get(
            label="comment_post_comment")
        previous_users = set()
        for previous_comment in comment.__class__.objects.filter(
            content_type=comment.content_type,
            object_pk=video.pk,
            is_public=True,
            is_removed=False,
            submit_date__lte=comment.submit_date,
            user__email__isnull=False).exclude(
            user__email='').exclude(pk=comment.pk):
            if (previous_comment.user not in previous_users and
                notification.should_send(previous_comment.user,
                                         comment_post_comment, "1") and
                not notification.should_send(previous_comment.user,
                                             admin_new_comment, "1")):
                previous_users.add(previous_comment.user)
                c = Context({ 'comment': comment,
                              'content_object': video,
                              'user_is_admin': False})
                message = t.render(c)
                EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL,
                             [previous_comment.user.email]).send(fail_silently=True)

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

tagging.register(Video)
tagging.register(OriginalVideo)

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
    if sender.is_active():
        # don't send the e-mail for videos that are already active
        return
    t = loader.get_template('localtv/submit_video/new_video_email.txt')
    c = Context({'video': sender})
    message = t.render(c)
    subject = '[%s] New Video in Review Queue: %s' % (sender.site.name,
                                                          sender)
    utils.send_notice('admin_new_submission',
                     subject, message,
                     sitelocation=sitelocation)

submit_finished.connect(send_new_video_email, weak=False)


def create_email_notices(app, created_models, verbosity, **kwargs):
    notification.create_notice_type('video_comment',
                                    'New comment on your video',
                                    'Someone commented on your video',
                                    default=2,
                                    verbosity=verbosity)
    notification.create_notice_type('comment_post_comment',
                                    'New comment after your comment',
                                    'Someone commented on a video after you',
                                    default=2,
                                    verbosity=verbosity)
    notification.create_notice_type('video_approved',
                                    'Your video was approved',
                                    'An admin approved your video',
                                    default=2,
                                    verbosity=verbosity)
    notification.create_notice_type('newsletter',
                                    'Newsletter',
                                    'Receive an occasional newsletter',
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
    notification.create_notice_type('admin_video_updated',
                                    'Video Updated',
                                    'A video from a service was updated',
                                    default=1,
                                    verbosity=verbosity)
    notification.create_notice_type('admin_new_playlist',
                                    'Request for Playlist Moderation',
                                    'A new playlist asked to be public',
                                    default=2,
                                    verbosity=verbosity)

models.signals.post_syncdb.connect(create_email_notices)

def delete_comments(sender, instance, **kwargs):
    from django.contrib.comments import get_model
    get_model().objects.filter(object_pk=instance.pk,
                               content_type__app_label='localtv',
                               content_type__model='video'
                               ).delete()
models.signals.pre_delete.connect(delete_comments,
                                  sender=Video)

### register pre-save handler for Tiers and payment due dates
models.signals.pre_save.connect(localtv.tiers.pre_save_set_payment_due_date,
                                sender=SiteLocation)
models.signals.pre_save.connect(localtv.tiers.pre_save_adjust_resource_usage,
                                sender=SiteLocation)
models.signals.post_save.connect(localtv.tiers.post_save_send_queued_mail,
                                 sender=SiteLocation)

def create_original_video(sender, instance=None, created=False, **kwargs):
    if not created:
        return # don't care about saving
    if not instance.website_url:
        # we don't know how to scrape this, so ignore it
        return
    new_data = dict(
        (field.name, getattr(instance, field.name))
        for field in VideoBase._meta.fields)
    OriginalVideo.objects.db_manager(instance._state.db).create(
        video=instance,
        thumbnail_updated=datetime.datetime.now(),
        **new_data)

def save_original_tags(sender, instance, created=False, **kwargs):
    if not created:
        # not a new tagged item
        return
    if not isinstance(instance.object, Video):
        # not a video
        return
    if (instance.object.when_submitted - datetime.datetime.now() >
        datetime.timedelta(seconds=10)):
        return
    try:
        original = instance.object.original
    except OriginalVideo.DoesNotExist:
        return
    tagging.models.TaggedItem.objects.db_manager(instance._state.db).create(
        tag=instance.tag, object=original)

ENABLE_ORIGINAL_VIDEO = not getattr(settings, 'LOCALTV_DONT_LOG_REMOTE_VIDEO_HISTORY', None)

if ENABLE_ORIGINAL_VIDEO:
    models.signals.post_save.connect(create_original_video,
                                     sender=Video)
    models.signals.post_save.connect(save_original_tags,
                                     sender=tagging.models.TaggedItem)

### The "stamp" set of features is a performance optimization for large
### deployments of Miro Community.
###
### The VIDEO_PUBLISHED_STAMP updates the mtime of a file whenever a Video instance
### is created or modified. If the stamp file is really old, then you can
### safely skip running management commands like update_index.

ENABLE_CHANGE_STAMPS = getattr(
    settings, 'LOCALTV_ENABLE_CHANGE_STAMPS', False)

def video_published_stamp_signal_listener(sender=None, instance=None, created=False, override_date=None, **kwargs):
    '''The purpose of the change stamp is to create a file on-disk that
    indicates when a new instance of the Video model has been published
    or modified.

    We actually simply update the stamp on every change or deletion to
    Video instances. This is slightly too aggressive: If a Video comes in
    from a feed and is not published, we will update the stamp needlessly.

    That is okay with me for now.
    '''
    update_stamp(name='video-published-stamp', override_date=override_date)

def site_has_at_least_one_feed_stamp_signal_listener(sender=None, instance=None, created=False, override_date=None, **kwargs):
    '''The purpose of this stamp is to signify to management scripts that this
    site has at least one Feed.

    Therefore, it listens to all .save()s on the Feed model and makes sure
    that the site-has-at-least-one-feed-stamp file exists.

    The site-has-at-least-one-feed-stamp stamp is unique in that its modification time
    is not very important.
    '''
    update_stamp(name='site-has-at-least-one-feed-stamp', override_date=override_date)

def site_has_at_least_one_saved_search_stamp_signal_listener(sender=None, instance=None, created=False, override_date=None, **kwargs):
    '''The purpose of this stamp is to signify to management scripts that this
    site has at least one SavedSearch.

    It is mostly the same as site_has_at_least_one_feed_stamp_signal_listener.'''
    update_stamp(name='site-has-at-least-saved-search-stamp', override_date=override_date)

def user_modified_stamp_signal_listener(sender=None, instance=None, created=False, override_date=None, **kwargs):
    '''The purpose of this stamp is to listen to the User model, and whenever
    a User changes (perhaps due to a change in the last_login value), we create
    a file on-disk to say so.

    Note taht this is a little too aggressive: Any change to a User will cause this stamp
    to get updated, not just last_login-related changes.

    That is okay with me for now.
    '''
    update_stamp(name='user-modified-stamp', override_date=override_date)

def video_needs_published_date_stamp_signal_listener(instance=None, **kwargs):
    if instance.when_published is None:
        update_stamp(name='video-needs-published-date-stamp')

def create_or_delete_video_needs_published_date_stamp():
    '''This function takes a look at all the Videos. If there are any
    that have a NULL value for date_published, it updates the stamp.

    If not, it deletes the stamp.'''
    if Video.objects.filter(when_published__isnull=True):
        update_stamp(name='video-needs-published-date-stamp')
    else:
        update_stamp(name='video-needs-published-date-stamp', delete_stamp=True)

def update_stamp(name, override_date=None, delete_stamp=False):
    path = os.path.join(settings.MEDIA_ROOT, '.' + name)
    if delete_stamp:
        try:
            os.unlink(path)
        except OSError, e:
            if e.errno == 2: # does not exist
                pass
            else:
                raise
        return

    try:
        utils.touch(path, override_date=override_date)
    except Exception, e:
        logging.error(e)

if ENABLE_CHANGE_STAMPS:
    models.signals.post_save.connect(video_published_stamp_signal_listener,
                                     sender=Video)
    models.signals.post_delete.connect(video_published_stamp_signal_listener,
                                       sender=Video)
    models.signals.post_save.connect(user_modified_stamp_signal_listener,
                                     sender=User)
    models.signals.post_delete.connect(user_modified_stamp_signal_listener,
                                       sender=User)
    models.signals.post_save.connect(site_has_at_least_one_feed_stamp_signal_listener,
                                     sender=Feed)
    models.signals.post_save.connect(site_has_at_least_one_saved_search_stamp_signal_listener,
                                     sender=SavedSearch)
    models.signals.post_save.connect(video_needs_published_date_stamp_signal_listener,
                                     sender=Video)
