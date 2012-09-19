from django.dispatch import Signal


#: This signal is fired when a :class:`.Video` is built from a
#: :class:`vidscraper.videos.Video`. It provides the following
#: arguments:
#:
#: - ``instance``: The created :class:`.Video` instance. This instance will not
#:                 have been saved.
#: - ``vidscraper_video``: The :class:`vidscraper.videos.Video` instance
#                          it was created from.
post_video_from_vidscraper = Signal(providing_args=["instance",
                                                    "vidscraper_video",
                                                    "using"])


#: This signal is fired when a :class:`.Video` is successfully submitted.
#: TODO: Depending on what happens with submit_video, this should perhaps be
#: moved elsewhere.
submit_finished = Signal()

#: This signal is fired from the mark_import_pending task, to optionally filter
#: what videos should be marked as active.  It provides the following
#: arguments:
#:
#: - ``active_set``: A :class:`django.db.models.QuerySet` of the videos that
#:                   we plan to mark as active.
#:
#: Handlers return either a :class:`django.db.models.Q` instance, or a
#: dictionary of filter keys/values.

pre_mark_as_active = Signal(providing_args=['active_set'])
