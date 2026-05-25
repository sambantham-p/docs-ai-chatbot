import logging
from time import perf_counter

import trafilatura

from app.schemas.responses import ExtractedContentResponse


logger = logging.getLogger(__name__)


def extract_article_content(
    url: str
) -> ExtractedContentResponse:
    """
    Extract clean article text from a webpage using trafilatura.
    """

    start_time = perf_counter()

    logger.info(
        "Starting article extraction | url=%s",
        url
    )

    try:

        downloaded = trafilatura.fetch_url(url)

        if not downloaded:

            logger.warning(
                "Failed to download article content | url=%s",
                url
            )

            return ExtractedContentResponse(
                success=False,
                error="Failed to download article content."
            )

        logger.debug(
            "Article downloaded successfully | url=%s",
            url
        )

        content = trafilatura.extract(
            downloaded,
            output_format="txt",
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )

        if not content:

            logger.warning(
                "Article extraction returned empty content | url=%s",
                url
            )

            return ExtractedContentResponse(
                success=False,
                error="Content extraction returned empty."
            )

        duration_ms = (perf_counter() - start_time) * 1000

        logger.info(
            (
                "Article extraction completed "
                "| url=%s | content_length=%s | duration_ms=%.2f"
            ),
            url,
            len(content),
            duration_ms
        )

        return ExtractedContentResponse(
            success=True,
            content=content
        )

    except Exception as error:

        logger.exception(
            "Unexpected error during article extraction | url=%s",
            url
        )

        return ExtractedContentResponse(
            success=False,
            error=str(error)
        )