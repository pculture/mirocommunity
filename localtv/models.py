# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2009, 2010, 2011, 2012 Participatory Culture Foundation
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
import itertools
import re
import urllib2
import mimetypes
import operator
import os
import logging
import sys
import traceback
import warnings

try:
    from PIL import Image as PILImage
except ImportError:
    import Image as PILImage
import time
from bs4 import BeautifulSoup

from daguerre.models import Image
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.moderation import CommentModerator, moderator
from django.contrib.sites.models import Site
from django.contrib.contenttypes import generic
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.core.signals import request_finished
from django.core.validators import ipv4_re
from django.template import Context, loader
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
import django.utils.html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

import vidscraper
from haystack import connections
from mptt.models import MPTTModel

from notification import models as notification
import tagging
import tagging.models

from localtv.exceptions import CannotOpenImageUrl
from localtv.templatetags.filters import sanitize
from localtv import utils
from localtv import settings as lsettings
from localtv.managers import SiteRelatedManager, VideoManager
from localtv.signals import post_video_from_vidscraper, submit_finished

def delete_if_exists(path):
    if default_storage.exists(path):
        default_storage.delete(path)

FORCE_HEIGHT_CROP = 1 # arguments for thumbnail resizing
FORCE_HEIGHT_PADDING = 2

VIDEO_SERVICE_REGEXES = (
    ('YouTube', r'http://gdata\.youtube\.com/feeds/'),
    ('YouTube', r'http://(www\.)?youtube\.com/'),
    ('blip.tv', r'http://(.+\.)?blip\.tv/'),
    ('Vimeo', r'http://(www\.)?vimeo\.com/'),
    ('Dailymotion', r'http://(www\.)?dailymotion\.com/rss'))


class Thumbnailable(models.Model):
    """
    A type of Model that has thumbnails generated for it.  Now that we're using
    Daguerre for thumbnails, this is just for backwards compatibility.
    """
    # we set this to "logo" for SiteSettings, 'icon' for  WidgetSettings
    thumbnail_attribute = 'thumbnail_file'

    class Meta:
        abstract = True

    @property
    def has_thumbnail(self):
        return bool(getattr(self, self.thumbnail_attribute))

    @property
    def thumbnail_path(self):
        thumb_file = getattr(self, self.thumbnail_attribute)
        if thumb_file:
            return thumb_file.name
        else:
            return ''


class SingletonManager(models.Manager):
    def get_current(self):
        current_site_settings = SiteSettings._default_manager.db_manager(
            self.db).get_current()
        singleton, created = self.get_or_create(
            site_settings = current_site_settings)
        if created:
            logging.debug("Created %s." % self.model)
        return singleton


class SiteSettings(Thumbnailable):
    """
    An extension to the django.contrib.sites site model, providing
    localtv-specific data.

    Fields:
     - site: A link to the django.contrib.sites.models.Site object
     - logo: custom logo image for this site
     - background: custom background image for this site (unused?)
     - admins: a collection of Users who have access to administrate this
       site_settings
     - status: one of SiteSettings.STATUS_CHOICES
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

    thumbnail_attribute = 'logo'

    DISABLED = 0
    ACTIVE = 1

    STATUS_CHOICES = (
        (DISABLED, _(u'Disabled')),
        (ACTIVE, _(u'Active')),
    )

    site = models.ForeignKey(Site, unique=True)
    logo = models.ImageField(upload_to=utils.UploadTo('localtv/sitesettings/logo/%Y/%m/%d/'), blank=True)
    background = models.ImageField(upload_to=utils.UploadTo('localtv/sitesettings/background/%Y/%m/%d/'),
                                   blank=True)
    admins = models.ManyToManyField('auth.User', blank=True,
                                    related_name='admin_for')
    status = models.IntegerField(choices=STATUS_CHOICES, default=ACTIVE)
    sidebar_html = models.TextField(blank=True)
    footer_html = models.TextField(blank=True)
    about_html = models.TextField(blank=True)
    tagline = models.CharField(max_length=4096, blank=True)
    css = models.TextField(blank=True)
    display_submit_button = models.BooleanField(default=True)
    submission_requires_login = models.BooleanField(default=False)
    playlists_enabled = models.IntegerField(default=1)
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

    objects = SiteRelatedManager()

    def __unicode__(self):
        return u'%s (%s)' % (self.site.name, self.site.domain)

    def user_is_admin(self, user):
        """
        Return True if the given User is an admin for this SiteSettings.
        """
        if not user.is_authenticated() or not user.is_active:
            return False

        if user.is_superuser:
            return True

        return self.admins.filter(pk=user.pk).exists()

    def should_show_dashboard(self):
        '''On /admin/, most sites will see a dashboard that gives them
        information at a glance about the site.

        Some sites want to disable that, which they can do by setting the
        LOCALTV_SHOW_ADMIN_DASHBOARD variable to False.

        In that case (in the default theme) the left-hand navigation
        will omit the link to the Dashboard, and also the dashboard itself
        will be an empty page with a META REFRESH that points to
        /admin/approve_reject/.'''
        return lsettings.SHOW_ADMIN_DASHBOARD


class NewsletterSettings(models.Model):
    DISABLED = 0
    FEATURED = 1
    POPULAR = 2
    CUSTOM = 3
    LATEST = 4
    
    STATUS_CHOICES = (
        (DISABLED, _(u'Disabled')),
        (FEATURED, _("5 most recently featured")),
        (POPULAR, _("5 most popular")),
        (LATEST, _("5 latest videos")),
        (CUSTOM, _("Custom selection")),
    )
    site_settings = models.OneToOneField(SiteSettings)
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
            videos = Video.objects.get_featured_videos(self.site_settings)
        elif self.status == NewsletterSettings.POPULAR:
            # popular over the last week
            videos = Video.objects.get_popular_videos(self.site_settings)
        elif self.status == NewsletterSettings.LATEST:
            videos = Video.objects.get_latest_videos(self.site_settings)
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
        subject = '[%s] Newsletter for %s' % (self.site_settings.site.name,
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
                   'site_settings': self.site_settings,
                   'site': self.site_settings.site}
        if extra_context:
            context.update(extra_context)
        return render_to_string('localtv/admin/newsletter.html',
                                context)


class WidgetSettingsManager(SiteRelatedManager):
    def _new_entry(self, site, using):
        ws = super(WidgetSettingsManager, self)._new_entry(site, using)
        try:
            site_settings = SiteSettings._default_manager.db_manager(
                using).get(site=site)
        except SiteSettings.DoesNotExist:
            pass
        else:
            if site_settings.logo:
                site_settings.logo.open()
                ws.icon = site_settings.logo
                ws.save()
        return ws


class WidgetSettings(Thumbnailable):
    """
    A Model which represents the options for controlling the widget creator.
    """
    thumbnail_attribute = 'icon'

    site = models.OneToOneField(Site)

    title = models.CharField(max_length=250, blank=True)
    title_editable = models.BooleanField(default=True)

    icon = models.ImageField(upload_to=utils.UploadTo('localtv/widgetsettings/icon/%Y/%m/%d/'), blank=True)
    icon_editable = models.BooleanField(default=False)

    css = models.FileField(upload_to=utils.UploadTo('localtv/widgetsettings/css/%Y/%m/%d/'), blank=True)
    css_editable = models.BooleanField(default=False)

    bg_color = models.CharField(max_length=20, blank=True)
    bg_color_editable = models.BooleanField(default=False)

    text_color = models.CharField(max_length=20, blank=True)
    text_color_editable = models.BooleanField(default=False)

    border_color = models.CharField(max_length=20, blank=True)
    border_color_editable = models.BooleanField(default=False)

    objects = WidgetSettingsManager()

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
    thumbnail_file = models.ImageField(upload_to=utils.UploadTo('localtv/source/thumbnail/%Y/%m/%d/'),
                                       blank=True)

    auto_approve = models.BooleanField(default=False)
    auto_update = models.BooleanField(default=True,
                                      help_text=_("If selected, new videos will"
                                                  " automatically be imported "
                                                  "from this source."))
    user = models.ForeignKey('auth.User', null=True, blank=True)
    auto_categories = models.ManyToManyField("Category", blank=True)
    auto_authors = models.ManyToManyField("auth.User", blank=True,
                                          related_name='auto_%(class)s_set')

    class Meta:
        abstract = True

    def update(self, video_iter, source_import, using='default',
               clear_rejected=False):
        """
        Imports videos from a feed/search.  `videos` is an iterable which
        returns :class:`vidscraper.videos.Video` objects.  We use
        :method:`.Video.from_vidscraper_video` to map the Vidscraper fields to
        Video attributes.

        If ``clear_rejected`` is ``True``, rejected versions of videos that are
        found in the ``video_iter`` will be deleted and re-imported.

        """
        author_pks = list(self.auto_authors.values_list('pk', flat=True))
        category_pks = list(self.auto_categories.values_list('pk', flat=True))

        import_opts = source_import.__class__._meta

        from localtv.tasks import video_from_vidscraper_video, mark_import_pending

        total_videos = 0

        try:
            for vidscraper_video in video_iter:
                total_videos += 1
                try:
                    video_from_vidscraper_video.delay(
                        vidscraper_video,
                        site_pk=self.site_id,
                        import_app_label=import_opts.app_label,
                        import_model=import_opts.module_name,
                        import_pk=source_import.pk,
                        status=Video.PENDING,
                        author_pks=author_pks,
                        category_pks=category_pks,
                        clear_rejected=clear_rejected,
                        using=using)
                except Exception:
                    source_import.handle_error(
                        'Import task creation failed for %r' % (
                            vidscraper_video.url,),
                        is_skip=True,
                        with_exception=True,
                        using=using)
        except Exception:
            source_import.fail(with_exception=True, using=using)
            return

        source_import.__class__._default_manager.using(using).filter(
            pk=source_import.pk
        ).update(
            total_videos=total_videos
        )
        mark_import_pending.delay(import_app_label=import_opts.app_label,
                                  import_model=import_opts.module_name,
                                  import_pk=source_import.pk,
                                  using=using)


class Feed(Source):
    """
    Feed to pull videos in from.

    If the same feed is used on two different sites, they will require two
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
    INACTIVE = 0
    ACTIVE = 1

    STATUS_CHOICES = (
        (INACTIVE, _(u'Inactive')),
        (ACTIVE, _(u'Active')),
    )

    feed_url = models.URLField(verify_exists=False)
    name = models.CharField(max_length=250)
    webpage = models.URLField(verify_exists=False, blank=True)
    description = models.TextField()
    last_updated = models.DateTimeField()
    when_submitted = models.DateTimeField(auto_now_add=True)
    etag = models.CharField(max_length=250, blank=True)
    calculated_source_type = models.CharField(max_length=255, blank=True, default='')
    status = models.IntegerField(choices=STATUS_CHOICES, default=INACTIVE)

    class Meta:
        unique_together = (
            ('feed_url', 'site'))
        get_latest_by = 'last_updated'

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_list_feed', [self.pk])

    def update(self, using='default', **kwargs):
        """
        Fetch and import new videos from this feed.

        """
        try:
            FeedImport.objects.using(using).get(source=self,
                                                status=FeedImport.STARTED)
        except FeedImport.DoesNotExist:
            pass
        else:
            logging.info('Skipping import of %s: already in progress' % self)
            return

        feed_import = FeedImport.objects.db_manager(using).create(source=self,
                                                auto_approve=self.auto_approve)

        video_iter = vidscraper.auto_feed(
            self.feed_url,
            max_results=None if self.status == self.INACTIVE else 100,
            api_keys=lsettings.API_KEYS,
        )

        try:
            video_iter.load()
        except Exception:
            feed_import.fail("Data loading failed for {source}",
                             with_exception=True, using=using)
            return

        self.etag = getattr(video_iter, 'etag', None) or ''
        self.last_updated = (getattr(video_iter, 'last_modified', None) or
                                 datetime.datetime.now())
        self.save()

        super(Feed, self).update(video_iter, source_import=feed_import,
                                 using=using, **kwargs)

    def source_type(self):
        return self.calculated_source_type

    def _calculate_source_type(self):
        video_service = self.video_service()
        if video_service is None:
            return u'Feed'
        else:
            return u'User: %s' % video_service

    def video_service(self):
        for service, regexp in VIDEO_SERVICE_REGEXES:
            if re.search(regexp, self.feed_url, re.I):
                return service


def pre_save_set_calculated_source_type(instance, **kwargs):
    # Always save the calculated_source_type
    instance.calculated_source_type = instance._calculate_source_type()
    # Plus, if the name changed, we have to recalculate all the Videos that depend on us.
    try:
        v = Feed.objects.using(instance._state.db).get(id=instance.id)
    except Feed.DoesNotExist:
        return instance
    if v.name != instance.name:
        # recalculate all the sad little videos' calculated_source_type
        for vid in instance.video_set.all():
            vid.save()
models.signals.pre_save.connect(pre_save_set_calculated_source_type,
                                sender=Feed)


class Category(MPTTModel):
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
        help_text=_("The name is used to identify the category almost "
                    "everywhere; for example, under a video or in a "
                    "category widget."))
    slug = models.SlugField(
        verbose_name='Category Slug',
        help_text=_("The \"slug\" is the URL-friendly version of the name.  It "
                    "is usually lower-case and contains only letters, numbers "
                    "and hyphens."))
    logo = models.ImageField(
        upload_to=utils.UploadTo('localtv/category/logo/%Y/%m/%d/'),
        blank=True,
        verbose_name='Thumbnail/Logo',
        help_text=_("Optional. For example: a leaf for 'environment' or the "
                    "logo of a university department."))
    description = models.TextField(
        blank=True, verbose_name='Description (HTML)',
        help_text=_("Optional. The description is not prominent by default, but"
                    " some themes may show it."))
    parent = models.ForeignKey(
        'self', blank=True, null=True,
        related_name='child_set',
        verbose_name='Category Parent',
        help_text=_("Categories, unlike tags, can have a hierarchy."))

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        unique_together = (
            ('slug', 'site'),
            ('name', 'site'))

    def __unicode__(self):
        return self.name

    def dashes(self):
        """
        Returns a string of em dashes equal to the :class:`Category`\ 's
        level. This is used to indent the category name in the admin
        templates.

        """
        return mark_safe('&mdash;' * self.level)

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_category', [self.slug])

    def approved_set(self):
        """
        Returns active videos for the category and its subcategories, ordered
        by decreasing best date.
        
        """
        opts = self._mptt_meta

        lookups = {
            'status': Video.ACTIVE,
            'categories__left__gte': getattr(self, opts.left_attr),
            'categories__left__lte': getattr(self, opts.right_attr),
            'categories__tree_id': getattr(self, opts.tree_id_attr)
        }
        lookups = self._tree_manager._translate_lookups(**lookups)
        return Video.objects.filter(**lookups).distinct()
    approved_set = property(approved_set)

    def unique_error_message(self, model_class, unique_check):
        return 'Category with this %s already exists.' % (
            unique_check[0],)


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

    def update(self, using='default', **kwargs):
        """
        Fetch and import new videos from this search.

        """
        try:
            SearchImport.objects.using(using).get(source=self,
                                                  status=SearchImport.STARTED)
        except SearchImport.DoesNotExist:
            pass
        else:
            logging.info('Skipping import of %s: already in progress' % self)
            return

        search_import = SearchImport.objects.db_manager(using).create(
            source=self,
            auto_approve=self.auto_approve
        )

        searches = vidscraper.auto_search(
            self.query_string,
            max_results=100,
            api_keys=lsettings.API_KEYS,
        )

        video_iters = []
        for video_iter in searches:
            try:
                video_iter.load()
            except Exception:
                search_import.handle_error(u'Skipping import of search results '
                               u'from %s' % video_iter.__class__.__name__,
                               with_exception=True, using=using)
                continue
            video_iters.append(video_iter)

        if video_iters:
            super(SavedSearch, self).update(itertools.chain(*video_iters),
                                            source_import=search_import,
                                            using=using, **kwargs)
        else:
            # Mark the import as failed if none of the searches could load.
            search_import.fail("All searches failed for {source}",
                               with_exception=False, using=using)

    def source_type(self):
        return u'Search'


class SourceImportIndex(models.Model):
    video = models.OneToOneField('Video', unique=True)
    index = models.PositiveIntegerField(blank=True, null=True)
    
    class Meta:
        abstract = True


class FeedImportIndex(SourceImportIndex):
    source_import = models.ForeignKey('FeedImport', related_name='indexes')


class SearchImportIndex(SourceImportIndex):
    source_import = models.ForeignKey('SearchImport', related_name='indexes')
    #: This is just the name of the suite that was used to get this index.
    suite = models.CharField(max_length=30, blank=True)


class SourceImportError(models.Model):
    message = models.TextField()
    traceback = models.TextField(blank=True)
    is_skip = models.BooleanField(help_text="Whether this error represents a "
                                            "video that was skipped.")
    datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class FeedImportError(SourceImportError):
    source_import = models.ForeignKey('FeedImport', related_name='errors')


class SearchImportError(SourceImportError):
    source_import = models.ForeignKey('SearchImport', related_name='errors')


class SourceImport(models.Model):
    STARTED = 'started'
    PENDING = 'pending'
    COMPLETE = 'complete'
    FAILED = 'failed'
    STATUS_CHOICES = (
        (STARTED, _('Started')),
        (PENDING, _('Pending haystack updates')),
        (COMPLETE, _('Complete')),
        (FAILED, _('Failed'))
    )
    start = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(blank=True, null=True)
    total_videos = models.PositiveIntegerField(blank=True, null=True)
    videos_imported = models.PositiveIntegerField(default=0)
    videos_skipped = models.PositiveIntegerField(default=0)
    #: Caches the auto_approve of the search on the import, so that the imported
    #: videos can be approved en masse at the end of the import based on the
    #: settings at the beginning of the import.
    auto_approve = models.BooleanField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES,
                              default=STARTED)

    class Meta:
        get_latest_by = 'start'
        ordering = ['-start']
        abstract = True

    def is_running(self):
        """
        Returns True if the SourceImport is currently running.
        """
        return self.status in (self.STARTED, self.PENDING)

    def set_video_source(self, video):
        """
        Sets the value of the correct field on the ``video`` to mark it as
        having the same source as this import. Must be implemented by
        subclasses.

        """
        raise NotImplementedError

    def get_videos(self, using='default'):
        raise NotImplementedError

    def handle_error(self, message, is_skip=False, with_exception=False,
                     using='default'):
        """
        Logs the error with the default logger and to the database.

        :param message: A human-friendly description of the error that does
                        not contain sensitive information.
        :param is_skip: ``True`` if the error results in a video being skipped.
                        Default: False.
        :param with_exception: ``True`` if exception information should be
                               recorded. Default: False.
        :param using: The database to use. Default: 'default'.

        """
        if with_exception:
            exc_info = sys.exc_info()
            logging.warn(message, exc_info=exc_info)
            tb = ''.join(traceback.format_exception(*exc_info))
        else:
            logging.warn(message)
            tb = ''
        self.errors.db_manager(using).create(message=message,
                                             source_import=self,
                                             traceback=tb,
                                             is_skip=is_skip)
        if is_skip:
            self.__class__._default_manager.using(using).filter(pk=self.pk
                        ).update(videos_skipped=models.F('videos_skipped') + 1)

    def get_index_creation_kwargs(self, video, vidscraper_video):
        return {
            'source_import': self,
            'video': video,
            'index': vidscraper_video.index
        }

    def handle_video(self, video, vidscraper_video, using='default'):
        """
        Creates an index instance connecting the video to this import.

        :param video: The :class:`Video` instance which was imported.
        :param vidscraper_video: The original video from :mod:`vidscraper`.
        :param using: The database alias to use. Default: 'default'

        """
        self.indexes.db_manager(using).create(
                    **self.get_index_creation_kwargs(video, vidscraper_video))
        self.__class__._default_manager.using(using).filter(pk=self.pk
                    ).update(videos_imported=models.F('videos_imported') + 1)

    def fail(self, message="Import failed for {source}", with_exception=False,
             using='default'):
        """
        Mark an import as failed, along with some post-fail cleanup.

        """
        self.status = self.FAILED
        self.last_activity = datetime.datetime.now()
        self.save()
        self.handle_error(message.format(source=self.source),
                          with_exception=with_exception, using=using)
        self.get_videos(using).delete()


class FeedImport(SourceImport):
    source = models.ForeignKey(Feed, related_name='imports')

    def set_video_source(self, video):
        video.feed_id = self.source_id

    def get_videos(self, using='default'):
        return Video.objects.using(using).filter(
                                        feedimportindex__source_import=self)


class SearchImport(SourceImport):
    source = models.ForeignKey(SavedSearch, related_name='imports')

    def set_video_source(self, video):
        video.search_id = self.source_id

    def get_videos(self, using='default'):
        return Video.objects.using(using).filter(
                                        searchimportindex__source_import=self)


class VideoBase(models.Model):
    """
    Base class between Video and OriginalVideo.  It would be simple enough to
    duplicate these fields, but this way it's easier to add more points of
    duplication in the future.
    """
    name = models.CharField(verbose_name="Video Name", max_length=250)
    description = models.TextField(verbose_name="Video Description (optional)",
                                   blank=True)
    thumbnail_url = models.URLField(verbose_name="Thumbnail URL (optional)",
                                    verify_exists=False, blank=True,
                                    max_length=400)

    class Meta:
        abstract = True

class OriginalVideo(VideoBase):

    VIDEO_ACTIVE, VIDEO_DELETED, VIDEO_DELETE_PENDING = range(3)

    video = models.OneToOneField('Video', related_name='original')
    thumbnail_updated = models.DateTimeField(blank=True)
    remote_video_was_deleted = models.IntegerField(default=VIDEO_ACTIVE)
    remote_thumbnail_hash = models.CharField(max_length=64, default='')

    taggeditem_set = generic.GenericRelation(tagging.models.TaggedItem,
                                             content_type_field='content_type',
                                             object_id_field='object_id')

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
                                                video.website_url,
                                                fields=fields,
                                                api_keys=lsettings.API_KEYS)
            except vidscraper.exceptions.VideoDeleted:
                remote_video_was_deleted = True
            except urllib2.URLError:
                # some kind of error Vidscraper couldn't handle; log it and
                # move on.
                logging.warning('exception while checking %r',
                                video.website_url, exc_info=True)
                return {}

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
                        site_settings=SiteSettings.objects.get_cached(
                                            site=self.video.site,
                                            using=self._state.db))
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
                    from localtv.tasks import (video_save_thumbnail,
                                               CELERY_USING)
                    video_save_thumbnail.delay(self.video.pk,
                                               using=CELERY_USING)
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
                    site_settings=SiteSettings.objects.get_cached(
                                        site=self.video.site,
                                        using=self._state.db))

        # And update the self instance to reflect the changes.
        for field in changed_fields:
            if field == 'tags':
                self.tags = get_or_create_tags(changed_fields[field])
            else:
                setattr(self, field, changed_fields[field])
        self.save()


class Video(Thumbnailable, VideoBase):
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
     - thumbnail_url: url to the thumbnail, if such a thing exists
     - user: if not None, the user who submitted this video
     - search: if not None, the SavedSearch from which this video came
     - video_service_user: if not blank, the username of the user on the video
       service who owns this video.  We can figure out the service from the
       website_url.
     - contact: a free-text field for anonymous users to specify some contact
       info
     - notes: a free-text field to add notes about the video
    """
    UNAPPROVED = 0
    ACTIVE = 1
    REJECTED = 2
    PENDING = 3

    STATUS_CHOICES = (
        (UNAPPROVED, _(u'Unapproved')),
        (ACTIVE, _(u'Active')),
        (REJECTED, _(u'Rejected')),
        (PENDING, _(u'Waiting on import to finish')),
    )

    site = models.ForeignKey(Site)
    thumbnail_file = models.ImageField(upload_to=utils.UploadTo('localtv/video/thumbnail/%Y/%m/%d/'),
                                       blank=True)
    categories = models.ManyToManyField(Category, blank=True)
    authors = models.ManyToManyField('auth.User', blank=True,
                                     related_name='authored_set')
    file_url = models.URLField(verify_exists=False, blank=True,
                               max_length=2048)
    file_url_length = models.IntegerField(null=True, blank=True)
    file_url_mimetype = models.CharField(max_length=60, blank=True)
    when_modified = models.DateTimeField(auto_now=True,
                                         db_index=True,
                                         default=datetime.datetime.now)
    when_submitted = models.DateTimeField(auto_now_add=True)
    when_approved = models.DateTimeField(null=True, blank=True)
    when_published = models.DateTimeField(null=True, blank=True)
    last_featured = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=UNAPPROVED)
    feed = models.ForeignKey(Feed, null=True, blank=True)
    website_url = models.URLField(
        verbose_name='Original Video Page URL (optional)',
        max_length=2048,
        verify_exists=False,
        blank=True)
    embed_code = models.TextField(verbose_name="Video <embed> code", blank=True)
    flash_enclosure_url = models.URLField(verify_exists=False, max_length=2048,
                                          blank=True)
    guid = models.CharField(max_length=250, blank=True)
    user = models.ForeignKey('auth.User', null=True, blank=True)
    search = models.ForeignKey(SavedSearch, null=True, blank=True)
    video_service_user = models.CharField(max_length=250, blank=True)
    video_service_url = models.URLField(verify_exists=False, blank=True)
    contact = models.CharField(verbose_name='E-mail (optional)', max_length=250,
                               blank=True)
    notes = models.TextField(verbose_name='Notes (optional)', blank=True)
    calculated_source_type = models.CharField(max_length=255, blank=True, default='')

    objects = VideoManager()

    taggeditem_set = generic.GenericRelation(tagging.models.TaggedItem,
                                             content_type_field='content_type',
                                             object_id_field='object_id')

    class Meta:
        ordering = ['-when_submitted']
        get_latest_by = 'when_modified'

    def __unicode__(self):
        return self.name

    def clean(self):
        if not self.embed_code and not self.file_url:
            raise ValidationError("Video has no embed code or file url.")

        qs = Video.objects.using(self._state.db).filter(site=self.site_id
                                              ).exclude(status=Video.REJECTED)

        if self.pk is not None:
            qs = qs.exclude(pk=self.pk)

        if self.guid and qs.filter(guid=self.guid).exists():
            raise ValidationError("Another video with the same guid "
                                  "already exists.")

        if (self.website_url and
            qs.filter(website_url=self.website_url).exists()):
            raise ValidationError("Another video with the same website url "
                                  "already exists.")

        if self.file_url and qs.filter(file_url=self.file_url).exists():
            raise ValidationError("Another video with the same file url "
                                  "already exists.")

    def clear_rejected_duplicates(self):
        """
        Deletes rejected copies of this video based on the file_url,
        website_url, and guid fields.

        """
        if not any((self.website_url, self.file_url, self.guid)):
            return

        q_filter = models.Q()
        if self.website_url:
            q_filter |= models.Q(website_url=self.website_url)
        if self.file_url:
            q_filter |= models.Q(file_url=self.file_url)
        if self.guid:
            q_filter |= models.Q(guid=self.guid)
        qs = Video.objects.using(self._state.db).filter(
            site=self.site_id,
            status=Video.REJECTED).filter(q_filter)
        qs.delete()

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_view_video', (),
                {'video_id': self.id,
                 'slug': slugify(self.name)[:30]})

    def save(self, **kwargs):
        """
        Adds support for an ```update_index`` kwarg, defaulting to ``True``.
        If this kwarg is ``False``, then no index updates will be run by the
        search index.

        """
        # This actually relies on logic in
        # :meth:`QueuedSearchIndex._enqueue_instance`
        self._update_index = kwargs.pop('update_index', True)
        super(Video, self).save(**kwargs)
    save.alters_data = True


    @classmethod
    def from_vidscraper_video(cls, video, status=None, commit=True,
                              using='default', source_import=None, site_pk=None,
                              authors=None, categories=None, update_index=True):
        """
        Builds a :class:`Video` instance from a
        :class:`vidscraper.videos.Video` instance. If `commit` is False,
        the :class:`Video` will not be saved, and the created instance will have
        a `save_m2m()` method that must be called after you call `save()`.

        """
        video_file = video.get_file()
        if video_file and video_file.expires is None:
            file_url = video_file.url
        else:
            file_url = None

        if status is None:
            status = cls.UNAPPROVED
        if site_pk is None:
            site_pk = settings.SITE_ID

        now = datetime.datetime.now()

        instance = cls(
            guid=video.guid or '',
            name=video.title or '',
            description=video.description or '',
            website_url=video.link or '',
            when_published=video.publish_datetime,
            file_url=file_url or '',
            file_url_mimetype=getattr(video_file, 'mime_type', '') or '',
            file_url_length=getattr(video_file, 'length', None),
            when_submitted=now,
            when_approved=now if status == cls.ACTIVE else None,
            status=status,
            thumbnail_url=video.thumbnail_url or '',
            embed_code=video.embed_code or '',
            flash_enclosure_url=video.flash_enclosure_url or '',
            video_service_user=video.user or '',
            video_service_url=video.user_url or '',
            site_id=site_pk
        )

        if instance.description:
            soup = BeautifulSoup(video.description)
            for tag in soup.find_all(
                'div', {'class': "miro-community-description"}):
                instance.description = unicode(tag)
                break
            instance.description = sanitize(instance.description,
                                            extra_filters=['img'])

        instance._vidscraper_video = video

        if source_import is not None:
            source_import.set_video_source(instance)

        def save_m2m():
            if authors:
                instance.authors = authors
            elif video.user:
                name = video.user
                if ' ' in name:
                    first, last = name.split(' ', 1)
                else:
                    first, last = name, ''
                author, created = User.objects.db_manager(using).get_or_create(
                    username=name[:30],
                    defaults={'first_name': first[:30],
                              'last_name': last[:30]})
                if created:
                    author.set_unusable_password()
                    author.save()
                    utils.get_profile_model()._default_manager.db_manager(using
                        ).create(user=author, website=video.user_url or '')
                instance.authors = [author]
            if categories:
                instance.categories = categories
            if video.tags:
                if settings.FORCE_LOWERCASE_TAGS:
                    fix = lambda t: t.lower().strip()
                else:
                    fix = lambda t: t.strip()
                tags = set(fix(tag) for tag in video.tags if tag.strip())
                for tag_name in tags:
                    tag, created = \
                        tagging.models.Tag._default_manager.db_manager(
                        using).get_or_create(name=tag_name)
                    tagging.models.TaggedItem._default_manager.db_manager(
                        using).create(
                        tag=tag, object=instance)
            if source_import is not None:
                source_import.handle_video(instance, video, using)
            post_video_from_vidscraper.send(sender=cls, instance=instance,
                                            vidscraper_video=video, using=using)
            if update_index:
                index = connections[using].get_unified_index().get_index(cls)
                index._enqueue_update(instance)

        if commit:
            instance.save(using=using, update_index=False)
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
        if SiteSettings.objects.db_manager(self._state.db).get(
            site=self.site_id).use_original_date and \
            self.when_published:
            return self.when_published
        return self.when_approved or self.when_submitted

    def source_type(self):
        if self.id and self.search_id:
            try:
                return u'Search: %s' % self.search
            except SavedSearch.DoesNotExist:
                return u''

        if self.id and self.feed_id:
            try:
                if self.feed.video_service():
                    return u'User: %s: %s' % (
                        self.feed.video_service(),
                        self.feed.name)
                else:
                    return 'Feed: %s' % self.feed.name
            except Feed.DoesNotExist:
                return ''

        if self.video_service_user:
            return u'User: %s: %s' % (self.video_service(),
                                      self.video_service_user)

        return ''

    def video_service(self):
        if not self.website_url:
            return

        url = self.website_url
        for service, regexp in VIDEO_SERVICE_REGEXES:
            if re.search(regexp, url, re.I):
                return service

    def when_prefix(self):
        """
        When videos are bulk imported (from a feed or a search), we list the
        date as "published", otherwise we show 'posted'.
        """
        site_settings = SiteSettings.objects.get_cached(site=self.site_id,
                                                        using=self._state.db)
        if self.when_published and site_settings.use_original_date:
            return 'published'
        else:
            return 'posted'

    @property
    def all_categories(self):
        """
        Returns a set of all the categories to which this video belongs.

        """
        categories = self.categories.all()
        if not categories:
            return categories
        q_list = []
        opts = Category._mptt_meta
        for category in categories:
            l = {
                'left__lte': getattr(category, opts.left_attr),
                'right__gte': getattr(category, opts.right_attr),
                'tree_id': getattr(category, opts.tree_id_attr)
            }
            l = Category._tree_manager._translate_lookups(**l)
            q_list.append(models.Q(**l))
        q = reduce(operator.or_, q_list)
        return Category.objects.using(self._state.db).filter(q)


def pre_save_video_set_calculated_source_type(instance, **kwargs):
    # Always recalculate the source_type field.
    instance.calculated_source_type = instance.source_type()
models.signals.pre_save.connect(pre_save_video_set_calculated_source_type,
                                sender=Video)


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
        ignored_bots = getattr(settings, 'LOCALTV_WATCH_IGNORED_USER_AGENTS',
                               ('bot', 'spider', 'crawler'))
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if user_agent and ignored_bots:
            for bot in ignored_bots:
                if bot in user_agent:
                    return

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
        site_settings = SiteSettings.objects.get_cached(site=video.site_id,
                                                        using=video._state.db)
        if site_settings.comments_required_login:
            return request.user and request.user.is_authenticated()
        else:
            return True

    def email(self, comment, video, request):
        # we do the import in the function because otherwise there's a circular
        # dependency
        from localtv.utils import send_notice

        site_settings = SiteSettings.objects.get_cached(site=video.site_id,
                                                        using=video._state.db)
        t = loader.get_template('comments/comment_notification_email.txt')
        c = Context({ 'comment': comment,
                      'content_object': video,
                      'user_is_admin': True})
        subject = '[%s] New comment posted on "%s"' % (video.site.name,
                                                       video)
        message = t.render(c)
        send_notice('admin_new_comment', subject, message,
                    site_settings=site_settings)

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
        site_settings = SiteSettings.objects.get_cached(site=video.site_id,
                                                        using=video._state.db)
        if site_settings.screen_all_comments:
            if not getattr(request, 'user'):
                return True
            else:
                return not site_settings.user_is_admin(request.user)
        else:
            return False

moderator.register(Video, VideoModerator)

tagging.register(Video)
tagging.register(OriginalVideo)

def finished(sender, **kwargs):
    SiteSettings.objects.clear_cache()
request_finished.connect(finished)

def tag_unicode(self):
    # hack to make sure that Unicode data gets returned for all tags
    if isinstance(self.name, str):
        self.name = self.name.decode('utf8')
    return self.name

tagging.models.Tag.__unicode__ = tag_unicode


def send_new_video_email(sender, **kwargs):
    site_settings = SiteSettings.objects.get_cached(site=sender.site_id,
                                                   using=sender._state.db)
    if sender.status == Video.ACTIVE:
        # don't send the e-mail for videos that are already active
        return
    t = loader.get_template('localtv/submit_video/new_video_email.txt')
    c = Context({'video': sender})
    message = t.render(c)
    subject = '[%s] New Video in Review Queue: %s' % (sender.site.name,
                                                          sender)
    utils.send_notice('admin_new_submission',
                     subject, message,
                     site_settings=site_settings)

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

if lsettings.ENABLE_ORIGINAL_VIDEO:
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

if lsettings.ENABLE_CHANGE_STAMPS:
    warnings.warn('LOCALTV_ENABLE_CHANGE_STAMPS is deprecated.',
                  DeprecationWarning)
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
