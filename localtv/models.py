import datetime
import itertools
import re
import urllib2
import mimetypes
import operator
import logging
import sys
import traceback
import warnings

import tagging
import tagging.models
import vidscraper
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.moderation import CommentModerator, moderator
from django.contrib.sites.models import Site
from django.contrib.contenttypes import generic
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.signals import request_finished
from django.core.validators import ipv4_re
from django.db import models
from django.template import Context, loader
from django.template.defaultfilters import slugify
from django.utils.html import escape as html_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from haystack import connections
from mptt.models import MPTTModel
from notification import models as notification

from localtv import utils, settings as lsettings
from localtv.managers import SiteRelatedManager, VideoManager
from localtv.signals import post_video_from_vidscraper, submit_finished
from localtv.templatetags.filters import sanitize


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
    thumbnail_attribute = 'thumbnail'

    class Meta:
        abstract = True

    @property
    def has_thumbnail(self):
        warnings.warn("has_thumbnail is deprecated and will be removed in a "
                      "future version.", DeprecationWarning)
        return bool(getattr(self, self.thumbnail_attribute))

    @property
    def thumbnail_path(self):
        warnings.warn("thumbnail_path is deprecated and will be removed in a "
                      "future version.", DeprecationWarning)
        thumb_file = getattr(self, self.thumbnail_attribute)
        if thumb_file:
            return thumb_file.name
        else:
            return ''


class SiteSettings(Thumbnailable):
    """
    A model for storing Site-specific settings (feature switches, custom HTML
    and CSS, etc) in the database rather than in settings files. Most of
    these can thus be set by site admins rather than sysadmins. There are
    also a few fields for storing site event state.

    """
    thumbnail_attribute = 'logo'

    #: Link to the Site these settings are for.
    site = models.OneToOneField(Site)

    ## Site styles ##
    #: Custom logo image for this site.
    logo = models.ImageField(upload_to=utils.UploadTo('localtv/sitesettings/logo/%Y/%m/%d/'), blank=True)

    #: Custom background image for this site.
    background = models.ImageField(upload_to=utils.UploadTo('localtv/sitesettings/background/%Y/%m/%d/'),
                                   blank=True)
    #: Arbitrary custom css overrides.
    css = models.TextField(blank=True)

    ## Custom HTML ##
    #: Subheader for the site.
    tagline = models.CharField(max_length=4096, blank=True)
    #: Arbitrary custom HTML which (currently) is used as a site description
    #: on the main page.
    sidebar_html = models.TextField(blank=True)
    #: Arbitrary custom HTML which displays in the footer of all non-admin pages.
    footer_html = models.TextField(blank=True)
    #: Arbitrary custom HTML which displays on the about page.
    about_html = models.TextField(blank=True)

    ## Site permissions ##
    #: A collection of Users who have administrative access to the site.
    admins = models.ManyToManyField('auth.User', blank=True,
                                    related_name='admin_for')
    #: Whether or not the Submit Video button should display or not.
    #: Doesn't affect whether videos can be submitted or not.
    #: See http://bugzilla.pculture.org/show_bug.cgi?id=19809
    display_submit_button = models.BooleanField(default=True)
    #: Whether or not users need to log in to submit videos.
    submission_requires_login = models.BooleanField(default=False)
    #: Whether or not an email address needs to be given with an
    #: unauthenticated video submission.
    submission_requires_email = models.BooleanField(default=False)

    ## Feature switches ##
    #: Whether playlist functionality is enabled.
    playlists_enabled = models.IntegerField(default=1)
    #: Whether the original publication date or date added to this site
    #: should be used for sorting videos.
    use_original_date = models.BooleanField(
        default=True,
        help_text="If set, use the original date the video was posted.  "
        "Otherwise, use the date the video was added to this site.")
    #: Whether comments should be held for moderation.
    screen_all_comments = models.BooleanField(
        verbose_name='Hold comments for moderation',
        default=True,
        help_text="Hold all comments for moderation by default?")
    #: Whether leaving a comment requires you to be logged in.
    comments_required_login = models.BooleanField(
        default=False,
        verbose_name="Require Login",
        help_text="If True, comments require the user to be logged in.")

    ## Tracking fields ##
    #: Whether a user has elected to hide the "get started" section in
    #: the admin interface.
    hide_get_started = models.BooleanField(default=False)

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
        """Returns True for backwards-compatibility."""
        warnings.warn("should_show_dashboard is deprecated and will be "
                      "removed in a future version.", DeprecationWarning)
        return True


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
            return html_escape(self.title)
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
                site.domain, html_escape(site.name))

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
    thumbnail = models.ImageField(upload_to=utils.UploadTo('localtv/source/thumbnail/%Y/%m/%d/'),
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
                        vidscraper_video.serialize(),
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
    description = models.TextField(blank=True)
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
        self.last_updated = datetime.datetime.now()
        if self.status == self.INACTIVE:
            # If these fields have already been changed, don't
            # override those changes. Don't unset the name field
            # if no further data is available.
            if self.name == self.feed_url:
                self.name = video_iter.title or self.name
            if not self.webpage:
                self.webpage = video_iter.webpage or ''
            if not self.description:
                self.description = video_iter.description or ''
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
    name = models.CharField(verbose_name="Video Name", max_length=250)
    description = models.TextField(verbose_name="Video Description (optional)",
                                   blank=True)
    thumbnail_url = models.URLField(verbose_name="Thumbnail URL (optional)",
                                    verify_exists=False, blank=True,
                                    max_length=400)
    thumbnail = models.ImageField(upload_to=utils.UploadTo('localtv/video/thumbnail/%Y/%m/%d/'),
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
    contact = models.CharField(verbose_name='Email (optional)', max_length=250,
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
        # clean is always run during ModelForm cleaning. If a model form is in
        # play, rejected videos don't matter; the submission of that form
        # should be considered valid. During automated imports, rejected
        # videos are not excluded.
        self._check_for_duplicates(exclude_rejected=True)

    def _check_for_duplicates(self, exclude_rejected=True):
        if not self.embed_code and not self.file_url:
            raise ValidationError("Video has no embed code or file url.")

        qs = Video.objects.using(self._state.db).filter(site=self.site_id)

        if exclude_rejected:
            qs = qs.exclude(status=Video.REJECTED)

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
            if video.user:
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
                instance.authors.add(author)
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
        if (hasattr(self, '_prefetched_objects_cache') and
                'taggeditem_set' in self._prefetched_objects_cache):
            return [item.tag for item in
                    self._prefetched_objects_cache['taggeditem_set']]
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
            http_file = urllib2.urlopen(request, timeout=5)
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
        site_settings = SiteSettings.objects.get_cached(self.site_id,
                                                        self._state.db)
        if site_settings.use_original_date and self.when_published:
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
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
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
        c = Context({'comment': comment,
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
               c = Context({'comment': comment,
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
                c = Context({'comment': comment,
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
    get_model().objects.using(instance._state.db).filter(
        object_pk=instance.pk,
        content_type__app_label='localtv',
        content_type__model='video'
        ).delete()
models.signals.pre_delete.connect(delete_comments,
                                  sender=Video)
