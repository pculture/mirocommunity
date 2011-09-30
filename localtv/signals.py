from django.dispatch import Signal


#: This signal is fired when a :class:`.Video` is built from a
#: :class:`vidscraper.suites.ScrapedVideo`. It provides the following
#: arguments:
#:
#: - ``instance``: The created :class:`.Video` instance. This instance will not
#:                 have been saved.
#: - ``scraped_video``: The :class:`vidscraper.suites.ScrapedVideo` instance it
#:                      was created from.
post_video_from_scraped = Signal(providing_args=["instance", "scraped_video",])
