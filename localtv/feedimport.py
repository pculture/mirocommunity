from localtv import models
def update_feeds(verbose=False):
    for feed in models.Feed.objects.filter(status=models.FEED_STATUS_ACTIVE):
        feed.update_items()


def update_saved_searches(verbose=False):
    for saved_search in models.SavedSearch.objects.all():
        saved_search.update_items()


def update_publish_date(verbose=False):
    import vidscraper
    for v in models.Video.objects.filter(when_published__isnull=True):
        try:
            d = vidscraper.auto_scrape(v.website_url, fields=['publish_date'])
        except:
            pass
        else:
            if d:
                v.when_published = d['publish_date']
                v.save()
