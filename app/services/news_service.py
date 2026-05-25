import logging
from time import perf_counter

from app.constants.news_constants import (
    MIN_FULL_CONTENT_LENGTH,
    RSS_FEEDS
)

from app.services.rss_service import parse_rss
from app.utils.extracter_utils import extract_article_content


logger = logging.getLogger(__name__)


def process_feeds(feed_urls: list[str] | None = None) -> dict:
    """
    Unified news processing pipeline.

    Handles:
    - No feed URLs  → process all configured feeds
    - Single URL    → process one feed
    - Multiple URLs → process multiple feeds

    Pipeline:
    1. Parse RSS feed
    2. Check whether RSS already contains full content
    3. If content is incomplete, fetch full article via trafilatura
    4. Return structured response
    """

    start_time = perf_counter()

    urls = feed_urls or RSS_FEEDS

    logger.info(
        "Starting news processing | total_feeds=%s",
        len(urls)
    )

    processed_feeds = []
    total_articles = 0

    for url in urls:

        feed_start = perf_counter()

        try:

            logger.info(
                "Processing RSS feed | url=%s",
                url
            )

            rss_articles = parse_rss(url)

            logger.info(
                "RSS parsed successfully | url=%s | articles_found=%s",
                url,
                len(rss_articles)
            )

            articles = []

            for article in rss_articles:

                processed_article = _process_article(article)

                articles.append(processed_article)

            processed_feeds.append({
                "feed": url,
                "count": len(articles),
                "articles": articles,
            })

            total_articles += len(articles)

            logger.info(
                (
                    "Feed processed successfully "
                    "| url=%s | articles_processed=%s | duration_ms=%.2f"
                ),
                url,
                len(articles),
                (perf_counter() - feed_start) * 1000
            )

        except Exception:

            logger.exception(
                "Failed to process RSS feed | url=%s",
                url
            )

            # Continue processing remaining feeds
            processed_feeds.append({
                "feed": url,
                "count": 0,
                "articles": [],
                "error": "Failed to process feed"
            })

    total_duration = (perf_counter() - start_time) * 1000

    logger.info(
        (
            "News processing completed "
            "| total_feeds=%s | total_articles=%s | duration_ms=%.2f"
        ),
        len(urls),
        total_articles,
        total_duration
    )

    return {
        "total_feeds": len(urls),
        "total_articles": total_articles,
        "feeds": processed_feeds,
    }


def _process_article(article: dict) -> dict:
    """
    Resolve full content for a single RSS article entry.
    Uses trafilatura to fetch from URL if RSS only has a summary.
    """

    title = article.title
    link = article.link

    logger.debug(
        "Processing article | title=%s | link=%s",
        title,
        link
    )

    content = article.content or ""
    content_source = article.content_source  or "summary"

    needs_fetch = (
        content_source == "summary"
        or len(content.strip()) < MIN_FULL_CONTENT_LENGTH
    )

    if needs_fetch and link:

        logger.debug(
            (
                "Fetching full article content "
                "| title=%s | source=%s"
            ),
            title,
            content_source
        )

        fetched = extract_article_content(link)

        if fetched.success and fetched.content:
            content = fetched.content
            content_source = "fetched"
            logger.debug(
                "Article content fetched successfully | title=%s",
                title
            )

        else:

            logger.warning(
                "Failed to fetch full article content | title=%s | link=%s",
                title,
                link
            )

    return {
        "title": title,
        "link": link,
        "published": article.published,
        "content": content,
        "content_source": content_source,
        "source": article.source,
    }