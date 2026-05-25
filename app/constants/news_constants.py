RSS_FEEDS = [
    # Full content feeds (content:encoded present)
    "https://www.vikatan.com/stories.rss?section-id=8962&time-period=last-24-hours",

    # Summary-only feeds (trafilatura will fetch full content)
    "https://www.thehindu.com/feeder/default.rss",
    "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "https://feeds.feedburner.com/ndtvnews-top-stories",
]

# Minimum character length to consider RSS content as "full"
MIN_FULL_CONTENT_LENGTH = 200
