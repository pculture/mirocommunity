import datetime
import re
import mimetypes
import operator
import logging
import sys
import traceback
import warnings
from hashlib import sha1

import tagging
import tagging.models
import vidscraper
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.moderation import CommentModerator, moderator
from django.contrib.sites.models import Site
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.signals import request_finished
from django.core.validators import ipv4_re
from django.db import models
from django.template import Context, loader
from django.utils.html import escape as html_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from haystack import connections, connection_router
from mptt.models import MPTTModel
from notification import models as notification
import requests
from slugify import slugify

from localtv import utils, settings as lsettings
from localtv.managers import SiteRelatedManager, VideoManager
from localtv.signals import post_video_from_vidscraper, submit_finished, pre_publish
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
    logo_contains_site_name = models.BooleanField()

    #: Custom background image for this site.
    background = models.ImageField(upload_to=utils.UploadTo('localtv/sitesettings/background/%Y/%m/%d/'),
                                   blank=True)
    #: Arbitrary custom css overrides.
    css = models.TextField(blank=True)

    ## Custom HTML ##
    # was footer_html, about_html
    #: Arbitrary custom HTML which displays in the footer of all non-admin pages.
    footer_content = models.TextField(blank=True)
    #: Arbitrary custom HTML which displays on the about page.
    site_description = models.TextField(blank=True)

    ## Custom API Keys/service settings ##
    google_analytics_ua = models.CharField('Google Analytics UA',
                                           max_length=20,
                                           blank=True)
    google_analytics_domain = models.CharField('Google Analytics domain',
                                               max_length=100,
                                               blank=True)
    #: Usernames that can be used to moderate comments.
    facebook_admins = models.CharField(max_length=200, blank=True)

    ## Site permissions ##
    #: A collection of Users who have administrative access to the site.
    admins = models.ManyToManyField('auth.User', blank=True,
                                    related_name='admin_for')
    # was display_submit_button
    #: Whether or not the Submit Video button should display or not.
    #: Doesn't affect whether videos can be submitted or not.
    #: See http://bugzilla.pculture.org/show_bug.cgi?id=19809
    submission_allowed = models.BooleanField(default=True)
    #: Whether or not users need to log in to submit videos.
    submission_requires_login = models.BooleanField(default=False)
    #: Whether or not an email address needs to be given with an
    #: unauthenticated video submission.
    submission_requires_email = models.BooleanField(default=False)

    ## Internal use ##
    #: Whether a user has elected to hide the "get started" section in
    #: the admin interface.
    hide_get_started = models.BooleanField(default=False)

    # Backwards-compat/deprecated fields
    tagline = models.CharField(max_length=4096, blank=True)
    sidebar_html = models.TextField(blank=True)
    screen_all_comments = models.BooleanField(
        verbose_name='Hold comments for moderation',
        default=True,
        help_text="Hold all comments for moderation by default?")
    comments_required_login = models.BooleanField(
        default=False,
        verbose_name="Require Login",
        help_text="If True, comments require the user to be logged in.")
    use_original_date = models.BooleanField(
        default=True,
        help_text="If set, use the original date the video was posted.  "
        "Otherwise, use the date the video was added to this site.")
    playlists_enabled = models.IntegerField(default=1)


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
            site_settings = SiteSettings.objects.get_cached(site, using)
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


class SourceImportIdentifier(models.Model):
    """
    Represents a single identifier for a video, seen during an import of a
    given source.

    """
    identifier_hash = models.CharField(max_length=40)
    source_id = models.PositiveIntegerField()
    source_content_type = models.ForeignKey(ContentType)
    source = generic.GenericForeignKey('source_content_type', 'source_id')

    def __unicode__(self):
        return self.identifier_hash


class SourceImport(models.Model):
    created_timestamp = models.DateTimeField(auto_now_add=True)
    modified_timestamp = models.DateTimeField(auto_now=True)
    is_complete = models.BooleanField(default=False)
    #: Denormalized field displaying (eventually accurate) count of
    #: errors during the import process.
    error_count = models.PositiveIntegerField(default=0)
    #: Denormalized field displaying (eventually accurate) count of
    #: videos imported during the import process.
    import_count = models.PositiveIntegerField(default=0)
    source_id = models.PositiveIntegerField()
    source_content_type = models.ForeignKey(ContentType)
    source = generic.GenericForeignKey('source_content_type', 'source_id')

    class Meta:
        get_latest_by = 'created_timestamp'
        ordering = ['-created_timestamp']

    def _get_identifier_hashes(self, vidscraper_video):
        identifiers = (
            vidscraper_video.guid,
            vidscraper_video.link,
            vidscraper_video.flash_enclosure_url,
            vidscraper_video.embed_code
        )
        if vidscraper_video.files is not None:
            identifiers += tuple(f.url for f in vidscraper_video.files
                                 if not f.expires)

        return [sha1(i).hexdigest() for i in identifiers if i]

    def is_seen(self, vidscraper_video):
        hashes = self._get_identifier_hashes(vidscraper_video)
        if not hashes:
            return False
        kwargs = {
            'source_id': self.source_id,
            'source_content_type': self.source_content_type,
            'identifier_hash__in': hashes,
        }
        return SourceImportIdentifier.objects.filter(**kwargs).exists()

    def mark_seen(self, vidscraper_video):
        hashes = self._get_identifier_hashes(vidscraper_video)
        # TODO: Use bulk_create.
        for identifier_hash in hashes:
            kwargs = {
                'source_id': self.source_id,
                'source_content_type': self.source_content_type,
                'identifier_hash': identifier_hash,
            }
            SourceImportIdentifier.objects.create(**kwargs)

    def run(self):
        auto_authors = list(self.source.auto_authors.all())
        auto_categories = list(self.source.auto_categories.all())
        try:
            iterators = self.source.get_iterators()
        except Exception:
            self.record_step(SourceImportStep.IMPORT_ERRORED,
                             with_traceback=True)
            return
        for iterator in iterators:
            try:
                for vidscraper_video in iterator:
                    try:
                        vidscraper_video.load()
                        if self.is_seen(vidscraper_video):
                            self.record_step(SourceImportStep.VIDEO_SEEN)
                            if self.source.stop_if_seen:
                                break
                            else:
                                continue
                        video = Video.from_vidscraper_video(
                            vidscraper_video,
                            status=Video.UNPUBLISHED,
                            commit=False,
                            source=self.source,
                            site_pk=self.source.site_id,
                            authors=auto_authors,
                            categories=auto_categories,
                            update_index=False,
                        )
                        try:
                            video.clean_fields()
                            video.validate_unique()
                        except ValidationError:
                            self.record_step(SourceImportStep.VIDEO_INVALID,
                                             with_traceback=True)

                        video.save(update_index=False)
                        try:
                            video.save_m2m()
                        except Exception:
                            video.delete()
                            raise
                        self.mark_seen(vidscraper_video)
                        self.record_step(SourceImportStep.VIDEO_IMPORTED,
                                         video=video)
                    except Exception:
                        self.record_step(SourceImportStep.VIDEO_ERRORED,
                                         with_traceback=True)
                    # Update timestamp (and potentially counts) after each video.
                    self.save()
            except Exception:
                self.record_step(SourceImportStep.IMPORT_ERRORED,
                                 with_traceback=True)

        # Pt 2: Mark videos active all at once.
        from localtv.tasks import haystack_batch_update
        if not self.source.moderate_imported_videos:
            videos = Video.objects.filter(sourceimportstep__source_import=self,
                                          status=Video.UNPUBLISHED)
            for receiver, response in pre_publish.send_robust(
                    sender=self, videos=videos):
                if response:
                    if isinstance(response, models.Q):
                        videos = videos.filter(response)
                    elif isinstance(response, dict):
                        videos = videos.filter(**response)

            videos.update(status=Video.PUBLISHED)
            video_pks = Video.objects.filter(sourceimportstep__source_import=self,
                                             status=Video.PUBLISHED
                                             ).values_list('pk', flat=True)
            if video_pks:
                opts = Video._meta
                haystack_batch_update.delay(opts.app_label, opts.module_name,
                                            pks=list(video_pks), remove=False)

        Video.objects.filter(sourceimportstep__source_import=self,
                             status=Video.UNPUBLISHED
                             ).update(status=Video.NEEDS_MODERATION)
        self.is_complete = True
        self.save()

    def record_step(self, step_type, video=None, with_traceback=False):
        if step_type in (SourceImportStep.VIDEO_ERRORED,
                         SourceImportStep.IMPORT_ERRORED):
            self.error_count += 1
        if step_type == SourceImportStep.VIDEO_IMPORTED:
            self.import_count += 1
        tb = traceback.format_exc() if with_traceback else ''
        self.steps.create(step_type=step_type,
                          video=video,
                          traceback=tb)


class SourceImportStep(models.Model):
    #: Something errored on the import level.
    IMPORT_ERRORED = 'import errored'
    #: A video was found to already be in the database - i.e. previously imported.
    VIDEO_SEEN = 'video seen'
    #: Something semi-expected is wrong with the video which prevents
    #: it from being imported.
    VIDEO_INVALID = 'video invalid'
    #: Something unexpected happened during an import of a video.
    VIDEO_ERRORED = 'video errored'
    #: A video was successfully imported.
    VIDEO_IMPORTED = 'video imported'
    STEP_TYPE_CHOICES = (
        (IMPORT_ERRORED, _(u'Import errored')),
        (VIDEO_SEEN, _(u'Video seen')),
        (VIDEO_INVALID, _(u'Video invalid')),
        (VIDEO_ERRORED, _(u'Video errored')),
        (VIDEO_IMPORTED, _(u'Video imported')),
    )
    step_type = models.CharField(max_length=14,
                                 choices=STEP_TYPE_CHOICES)
    video = models.OneToOneField('Video',
                                 blank=True,
                                 null=True,
                                 on_delete=models.SET_NULL)
    traceback = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    source_import = models.ForeignKey(SourceImport, related_name='steps')

    def __unicode__(self):
        return unicode(self.step_type)


class Source(Thumbnailable):
    """
    An abstract base class to represent things which are sources of multiple
    videos.  Current subclasses are Feed and SavedSearch.
    """
    site = models.ForeignKey(Site)
    thumbnail = models.ImageField(upload_to=utils.UploadTo('localtv/source/thumbnail/%Y/%m/%d/'),
                                  blank=True)

    modified_timestamp = models.DateTimeField(auto_now=True)
    created_timestamp = models.DateTimeField(auto_now_add=True)

    moderate_imported_videos = models.BooleanField(default=False)
    disable_imports = models.BooleanField(default=False)
    auto_categories = models.ManyToManyField("Category", blank=True)
    auto_authors = models.ManyToManyField("auth.User", blank=True,
                                          related_name='auto_%(class)s_set')

    imports = generic.GenericRelation(SourceImport,
                                      content_type_field='source_content_type',
                                      object_id_field='source_id')

    class Meta:
        abstract = True

    def start_import(self):
        imp = SourceImport()
        imp.source = self
        imp.save()
        imp.run()


class Feed(Source):
    # Feeds are expected to stay in the same order.
    stop_if_seen = True
    # was "feed_url"
    original_url = models.URLField(verify_exists=False)

    # Feed metadata
    name = models.CharField(max_length=250)
    # Was "webpage"
    external_url = models.URLField(verify_exists=False, blank=True)
    description = models.TextField(blank=True)
    etag = models.CharField(max_length=250, blank=True)

    update_metadata = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_list_feed', [self.pk])

    def get_iterators(self):
        iterator = vidscraper.auto_feed(
            self.original_url,
            # We'll stop at the first previously-seen video.
            max_results=None,
            api_keys=lsettings.API_KEYS,
        )
        iterator.load()

        save = False

        etag = getattr(iterator, 'etag', None) or ''
        if (etag and etag != self.etag):
            self.etag = etag
            save = True

        if self.update_metadata:
            # If these fields have already been changed, don't
            # override those changes. Don't unset the name field
            # if no further data is available.
            if self.name == self.original_url:
                self.name = iterator.title or self.name
            if not self.external_url:
                self.external_url = iterator.webpage or ''
            if not self.description:
                self.description = iterator.description or ''
            # Only do this on the first run (for now.)
            self.update_metadata = False
            save = True

        if save:
            self.save()

        return [iterator]


class SavedSearch(Source):
    """
    A set of keywords to regularly pull in new videos from.

    """
    # Searches may have seen entries before unseen.
    stop_if_seen = False
    query_string = models.TextField()

    def __unicode__(self):
        return self.query_string

    def get_iterators(self):
        return vidscraper.auto_search(
            self.query_string,
            max_results=100,
            api_keys=lsettings.API_KEYS,
        )


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
            'status': Video.PUBLISHED,
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


class Video(Thumbnailable):
    UNPUBLISHED = 'unpublished'
    NEEDS_MODERATION = 'needs moderation'
    PUBLISHED = 'published'
    HIDDEN = 'hidden'

    STATUS_CHOICES = (
        (UNPUBLISHED, _(u'Unpublished')),
        (NEEDS_MODERATION, _(u'Needs moderation')),
        (PUBLISHED, _(u'Published')),
        (HIDDEN, _(u'Hidden')),
    )

    # Backwards-compat
    ACTIVE = PUBLISHED
    REJECTED = HIDDEN
    UNAPPROVED = NEEDS_MODERATION

    # Video core data
    #: This field contains a URL which a user gave as "the" URL
    #: for this video. It may or may not be the same as ``external_url``
    #: or a file url. It may not even exist, if they're using embedding.
    original_url = models.URLField(max_length=2048,
                                   verify_exists=False,
                                   blank=True)

    # Video metadata
    #: This field contains a URL to a web page that is the canonical HTML
    #: home of the video as best as we can tell.
    # Was website_url
    external_url = models.URLField(
        verbose_name='Original Video Page URL (optional)',
        max_length=2048,
        verify_exists=False,
        blank=True)
    embed_code = models.TextField(verbose_name="Video <embed> code", blank=True)
    flash_enclosure_url = models.URLField(verify_exists=False, max_length=2048,
                                          blank=True)
    name = models.CharField(verbose_name="Video Name", max_length=250)
    description = models.TextField(verbose_name="Video Description (optional)",
                                   blank=True)
    thumbnail = models.ImageField(upload_to=utils.UploadTo('localtv/video/thumbnail/%Y/%m/%d/'),
                                  blank=True)
    categories = models.ManyToManyField(Category, blank=True)
    authors = models.ManyToManyField('auth.User', blank=True,
                                     related_name='authored_set')
    guid = models.CharField(max_length=250, blank=True)

    taggeditem_set = generic.GenericRelation(tagging.models.TaggedItem,
                                             content_type_field='content_type',
                                             object_id_field='object_id')

    # Owner info.
    # Was "user"
    owner = models.ForeignKey('auth.User', null=True, blank=True)
    # was "contact"
    owner_email = models.EmailField(verbose_name='Email (optional)',
                                    max_length=250,
                                    blank=True)
    owner_session = models.ForeignKey('sessions.Session', blank=True, null=True)

    # Source info.
    feed = models.ForeignKey(Feed, null=True, blank=True)
    search = models.ForeignKey(SavedSearch, null=True, blank=True)
    # Was video_service_user and video_service_url
    external_user = models.CharField(max_length=250, blank=True)
    external_user_url = models.URLField(verify_exists=False, blank=True)
    # was "thumbnail_url"
    external_thumbnail_url = models.URLField(verbose_name="Thumbnail URL (optional)",
                                             verify_exists=False, blank=True,
                                             max_length=400)

    # Other internal use.
    site = models.ForeignKey(Site)
    status = models.CharField(max_length=16,
                              choices=STATUS_CHOICES,
                              default=UNPUBLISHED)
    # was "when_modified".
    modified_timestamp = models.DateTimeField(auto_now=True)
    # was "when_submitted"
    created_timestamp = models.DateTimeField(auto_now_add=True)
    # was "when_approved".
    published_datetime = models.DateTimeField(null=True, blank=True)
    # was when_published
    external_published_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Format: yyyy-mm-dd hh:mm:ss')
    # was last_featured
    featured_datetime = models.DateTimeField(null=True, blank=True)

    # Deprecated fields
    # Use case unclear. Dump it ASAP.
    notes = models.TextField(verbose_name='Notes (optional)', blank=True)

    objects = VideoManager()

    class Meta:
        ordering = ['-created_timestamp']
        get_latest_by = 'modified_timestamp'

    def __unicode__(self):
        return self.name

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
                              source=None, site_pk=None, authors=None,
                              categories=None, update_index=True):
        """
        Builds a :class:`Video` instance from a
        :class:`vidscraper.videos.Video` instance. If `commit` is False,
        the :class:`Video` will not be saved, and the created instance will have
        a `save_m2m()` method that must be called after you call `save()`.

        """
        if status is None:
            status = cls.NEEDS_MODERATION
        if site_pk is None:
            site_pk = settings.SITE_ID

        now = datetime.datetime.now()

        instance = cls(
            guid=video.guid or '',
            name=video.title or '',
            description=video.description or '',
            published_datetime=now if status == cls.PUBLISHED else None,
            status=status,
            external_url=video.link or '',
            external_published_datetime=video.publish_datetime,
            external_thumbnail_url=video.thumbnail_url or '',
            embed_code=video.embed_code or '',
            flash_enclosure_url=video.flash_enclosure_url or '',
            external_user=video.user or '',
            external_user_url=video.user_url or '',
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

        if isinstance(source, Feed):
            instance.feed = source
        elif isinstance(source, SavedSearch):
            instance.search = source

        def save_m2m():
            if authors:
                instance.authors = authors
            if video.user:
                name = video.user
                if ' ' in name:
                    first, last = name.split(' ', 1)
                else:
                    first, last = name, ''
                author, created = User.objects.get_or_create(
                    username=name[:30],
                    defaults={'first_name': first[:30],
                              'last_name': last[:30]})
                if created:
                    author.set_unusable_password()
                    author.save()
                    utils.get_profile_model()._default_manager.create(
                        user=author, website=video.user_url or '')
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
                        tagging.models.Tag._default_manager.get_or_create(name=tag_name)
                    tagging.models.TaggedItem._default_manager.create(
                        tag=tag, object=instance)
            if video.files:
                for video_file in video.files:
                    if video_file.expires is None:
                        VideoFile.objects.create(video=instance,
                                                 url=video_file.url,
                                                 length=video_file.length,
                                                 mimetype=video_file.mime_type)
            from localtv.tasks import video_save_thumbnail
            video_save_thumbnail.delay(instance.pk)
            post_video_from_vidscraper.send(sender=cls, instance=instance,
                                            vidscraper_video=video)
            if update_index:
                using = connection_router.for_write()[0]
                index = connections[using].get_unified_index().get_index(cls)
                index._enqueue_update(instance)

        if commit:
            instance.save(update_index=False)
            save_m2m()
        else:
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
        return Category.objects.filter(q)


class VideoFile(models.Model):
    video = models.ForeignKey(Video, related_name='files')
    url = models.URLField(verify_exists=False, max_length=2048)
    length = models.PositiveIntegerField(null=True, blank=True)
    mimetype = models.CharField(max_length=60, blank=True)

    def fetch_metadata(self):
        """
        Do a HEAD request on self.url to try to get metadata
        (self.length and self.mimetype).

        Note that while this method fills in those attributes, it does *not*
        call self.save() - so be sure to do so after calling this method!

        """
        if not self.url:
            return

        try:
            response = requests.head(self.url, timeout=5)
            if response.status_code == 302:
                response = requests.head(response.headers['location'],
                                         timeout=5)
        except Exception:
            pass
        else:
            if response.status_code != 200:
                return
            self.length = response.headers.get('content-length')
            self.mimetype = response.headers.get('content-type', '')
            if self.mimetype in ('application/octet-stream', ''):
                # We got a not-useful MIME type; guess!
                guess = mimetypes.guess_type(self.url)
                if guess[0] is not None:
                    self.mimetype = guess[0]


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
    if sender.status == Video.PUBLISHED:
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
    get_model().objects.filter(
        object_pk=instance.pk,
        content_type__app_label='localtv',
        content_type__model='video'
        ).delete()
models.signals.pre_delete.connect(delete_comments,
                                  sender=Video)
