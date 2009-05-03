from localtv.models import Feed, FEED_STATUS_ACTIVE

def update_feeds(verbose=False):
    for feed in Feed.objects.filter(status=FEED_STATUS_ACTIVE):
        feed.update_items()
