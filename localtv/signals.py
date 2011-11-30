from django.dispatch import Signal


#: This signal is fired when a :class:`.Video` is built from a
#: :class:`vidscraper.suites.base.Video`. It provides the following
#: arguments:
#:
#: - ``instance``: The created :class:`.Video` instance. This instance will not
#:                 have been saved.
#: - ``vidscraper_video``: The :class:`vidscraper.suites.base.Video` instance
#                          it was created from.
post_video_from_vidscraper = Signal(providing_args=["instance",
                                                    "vidscraper_video",
                                                    "using"])