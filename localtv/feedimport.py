from localtv import models
def update_feeds(verbose=False):
    for feed in models.Feed.objects.filter(status=models.FEED_STATUS_ACTIVE):
        feed.update_items()


def update_saved_searches(verbose=False):
    for saved_search in models.SavedSearch.objects.all():
        saved_search.update_items()
