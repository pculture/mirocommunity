Miro Community 1.9 Release Notes
================================

* Renamed :class:`~localtv.SiteLocation` to
  :class:`~localtv.SiteSettings`.
* Video submission extra_init hack removed and replaced with
  class-based views. Though these are not strictly
  backwards-compatible from the backend, the user experience and
  template contexts should be the same.

Miro Community 1.8.5 Release Notes
==================================

* Corrected a bug in feed import thumbnail handling.

Miro Community 1.8.4 Release Notes
==================================

* Corrected database referencing during source imports.
* Eliminated a thumbnail vs. source import race condition which was
  re-marking videos as pending.

Miro Community 1.8.3 Release Notes
==================================

* Brought test cases and example project dependencies up to date.
* Corrected some missing imports.
* Added a catch for errors while saving video m2m relationships during
  source imports.

Miro Community 1.8.2 Release Notes
==================================

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

Miro Community 1.8.1 Release Notes
==================================

* Various bugfixes for issues raised in the 1.8 release, such as:
   * Listing sorting
   * Feed caching
   * Video submission templates and template context
   * Feed unicode errors
* Removed patch_settings hack from :mod:`localtv.tasks`

Miro Community 1.8 Release Notes
================================

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
