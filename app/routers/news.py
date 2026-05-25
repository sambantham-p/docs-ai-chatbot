import logging
from fastapi import APIRouter, HTTPException, status
from app.constants.news_constants import RSS_FEEDS
from app.schemas.requests import ProcessNewsRequest
from app.schemas.responses import ProcessNewsResponse
from app.services.news_service import process_feeds


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news")


@router.post("/", response_model=ProcessNewsResponse)
async def news_endpoint(request: ProcessNewsRequest) -> ProcessNewsResponse:
  # Determine which URLs to process
    if request.urls:
        cleaned_urls = [url.strip() for url in request.urls if url and url.strip()]

        if not cleaned_urls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one valid RSS feed URL is required."
            )
    else:
        # No URLs provided — fall back to configured feeds
        cleaned_urls = RSS_FEEDS

    # Process feeds
    try:
        result = process_feeds(cleaned_urls)
        logger.info(f"Processed {result['total_feeds']} feeds with {result['total_articles']} articles.")
        logger.debug(f"Feed processing details: {result['feeds']}")
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process news feeds: {str(error)}"
        )

    # Nothing came back
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No articles found from the provided feeds."
        )

    return ProcessNewsResponse(**result)