import logging
from time import perf_counter

import feedparser

from app.constants.news_constants import MIN_FULL_CONTENT_LENGTH
from app.schemas.responses import ArticleResponse


logger = logging.getLogger(__name__)


def parse_rss(feed_url: str) -> list[ArticleResponse]:
    """
    Parse RSS feed and return structured article models.

    Priority:
    1. content:encoded -> full content from RSS
    2. summary         -> partial content, later enriched via trafilatura
    """

    start_time = perf_counter()

    logger.info(
        "Starting RSS parsing | feed_url=%s",
        feed_url
    )

    try:

        feed = feedparser.parse(feed_url)

        if getattr(feed, "bozo", False):

            logger.warning(
                "RSS feed parsing warning | feed_url=%s | error=%s",
                feed_url,
                getattr(feed, "bozo_exception", "Unknown parsing issue")
            )

        feed_title = feed.feed.get("title", "Unknown Feed")

        logger.info(
            "RSS feed fetched successfully | feed_url=%s | feed_title=%s",
            feed_url,
            feed_title
        )

        articles: list[ArticleResponse] = []

        for index, entry in enumerate(feed.entries, start=1):

            content = ""
            content_source = "rss"

            title = entry.get("title")
            link = entry.get("link")

            logger.debug(
                "Processing RSS entry | index=%s | title=%s",
                index,
                title
            )

            # Full content from RSS
            if "content" in entry and entry.content:

                raw_content = entry.content[0].value

                if (
                    raw_content
                    and len(raw_content.strip()) >= MIN_FULL_CONTENT_LENGTH
                ):

                    content = raw_content

                    logger.debug(
                        (
                            "Using full RSS content "
                            "| title=%s | content_length=%s"
                        ),
                        title,
                        len(content)
                    )

            # Fallback to summary/snippet
            if not content:

                content = entry.get("summary", "")
                content_source = "summary"

                logger.debug(
                    (
                        "Using RSS summary content "
                        "| title=%s | content_length=%s"
                    ),
                    title,
                    len(content)
                )

            article = ArticleResponse(
                title=title,
                link=link,
                published=entry.get("published"),
                content=content,
                content_source=content_source,
                source=feed_url
            )

            articles.append(article)

        duration_ms = (perf_counter() - start_time) * 1000

        logger.info(
            (
                "RSS parsing completed "
                "| feed_url=%s | total_articles=%s | duration_ms=%.2f"
            ),
            feed_url,
            len(articles),
            duration_ms
        )

        return articles

    except Exception:

        logger.exception(
            "Failed to parse RSS feed | feed_url=%s",
            feed_url
        )

        raise