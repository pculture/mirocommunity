
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

* :class:`Feed imports <localtv.FeedImport>` and :class:`Search imports <localtv.SearchImport>` are now tracked in the database.
* Imports are handled asynchronously with :mod:`celery`, for a more responsive user experience.
* :mod:`mirocommunity` now uses Django 1.3, including django.contrib.staticfiles. See the `Django 1.3 release notes`_ for more details.

.. _Django 1.3 release notes: https://docs.djangoproject.com/en/dev/releases/1.3/

Backwards-incompatible changes
++++++++++++++++++++++++++++++

* ``localtv.context_processor`` is now located at ``localtv.context_processors.localtv`` and no longer adds ``request`` to the context. The request can be included in the context by adding ``django.core.context_processors.request`` to the ``TEMPLATE_CONTEXT_PROCESSORS`` setting.
* :meth:`request.sitelocation` has been removed in favor of the more explicit :meth:`SiteLocation.objects.get_current`.
* ``localtv.FixAJAXMiddleware`` was moved to ``localtv.middleware.FixAJAXMiddleware``.
* ``localtv.SiteLocationMiddleware`` was moved to ``localtv.middleware.UserIsAdminMiddleware`` and no longer provides a shortcut method for fetching :class:`~localtv.SiteLocation`\ s on the request.

Other changes
+++++++++++++

* Most code related to scraping videos was pushed back upstream to :mod:`vidscraper`.
