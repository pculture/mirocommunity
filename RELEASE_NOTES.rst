Miro Community 1.10.0
=====================

* Upgraded to vidscraper 1.0.X.
* Switched thumbnail saving to use ImageFields.
* Upgraded theme handling.
* Moved "submission requires email address" setting to SiteSettings.
* Removed OriginalVideo model.
* Removed filesystem timestamps.
* Removed legacy commands: update_index_in_tmpdir
* Upgraded daguerre to use more efficient bulk adjustments.
* Set up amara use as default for video embeds.
* Improved feed efficiency with prefetch_related.
* Corrected issues with relative thumbnail URLs in widgets and feeds.

Miro Community 1.9.1
====================

* Switched to nose for tests.
* Added tox integration.
* Added selenium tests.
* Cleaned up grid list CSS/HTML.
* Moved auth functionality to top navbar.
* Switched adding/editing sources to use pages rather than overlays.
* Made sure haystack indexing pks are distinct.
* Switched social authentication to django-social-auth.
* Removed "Newsletter" functionality.
* Corrected video thumbnail handling in generated feeds.

Miro Community 1.9
==================

* Renamed :class:`~localtv.SiteLocation` to
  :class:`~localtv.SiteSettings`.
* Video submission extra_init hack removed and replaced with
  class-based views. Though these are not strictly
  backwards-compatible from the backend, the user experience and
  template contexts should be the same.
* New responsive front-end styles using sass/compass.
* New documentation, esp. as regards contributing to miro community.
* Switched to Django 1.4.
* Switched from django-voting to built-in contrib voting functionality.
* Purged all tiers-related code.
* Switched to django-daguerre for thumbnail resizing.
* Added read-only tastypie API for some aspects of Miro Community.
* Improved/simplified search code.
* Set up Category model to use django-mptt.
* Stopped using bitly to store long file urls.
* Moved :class:`Video` validation to the model class from the :func:`video_from_vidscraper_video` task.


Miro Community 1.8.6
====================

* Bumped Django requirement due to security releases.
* Stopped verification of submitted URLs' existence.

Miro Community 1.8.5
====================

* Corrected a bug in feed import thumbnail handling.

Miro Community 1.8.4
====================

* Corrected database referencing during source imports.
* Eliminated a thumbnail vs. source import race condition which was
  re-marking videos as pending.

Miro Community 1.8.3
====================

* Brought test cases and example project dependencies up to date.
* Corrected some missing imports.
* Added a catch for errors while saving video m2m relationships during
  source imports.

Miro Community 1.8.2
====================

* Added instance creation methods to new test cases.
* Disabled haystack indexing during fixture loading for legacy tests.
* Disabled haystack indexing during source imports.
* Added bulk indexing/removal support.
* Added flexible class-based sorting for SortFilter classes.
* Corrected feed caching issues.
* Fixed non-functional search feeds.
* Standardized handling of video popularity between the front page and
  the popular videos listing page.
	* This includes a new ``update_popularity`` management command,
	  which should be run at least once per day.
* Fix to video preview size in the admin live search.
* Fix for the admin unapproved videos feed.
* Deleting a source, user, or site will now remove all related videos
  from the search index.

Miro Community 1.8.1
====================

* Various bugfixes for issues raised in the 1.8 release, such as:
   * Listing sorting
   * Feed caching
   * Video submission templates and template context
   * Feed unicode errors
* Removed patch_settings hack from :mod:`localtv.tasks`

Miro Community 1.8
==================

New Features
++++++++++++

* :class:`Feed imports <localtv.FeedImport>` and :class:`Search
  imports <localtv.SearchImport>` are now tracked in the database.
* Imports are handled asynchronously with :mod:`celery`, for a more
  responsive user experience.
* :mod:`mirocommunity` now uses Django 1.3, including
  ``django.contrib.staticfiles``. See the `Django 1.3 release notes`_
  for more details.

.. _Django 1.3 release notes: https://docs.djangoproject.com/en/dev/releases/1.3/


Backwards-incompatible changes
++++++++++++++++++++++++++++++

* ``localtv.context_processor`` is now located at
  ``localtv.context_processors.localtv`` and no longer adds
  ``request`` to the context. The request can be included in the
  context by adding ``django.core.context_processors.request`` to the
  ``TEMPLATE_CONTEXT_PROCESSORS`` setting.
* :meth:`request.sitelocation` has been removed in favor of the more
  explicit :meth:`SiteLocation.objects.get_current`.
* ``localtv.FixAJAXMiddleware`` was moved to
  ``localtv.middleware.FixAJAXMiddleware``.
* ``localtv.SiteLocationMiddleware`` was moved to
  ``localtv.middleware.UserIsAdminMiddleware`` and no longer provides
  a shortcut method for fetching :class:`~localtv.SiteLocation`\ s on
  the request.


Other changes
+++++++++++++

* Most code related to scraping videos was pushed back upstream to
  :mod:`vidscraper`.
