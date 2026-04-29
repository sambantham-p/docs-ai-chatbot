import asyncio
import logging
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse
import requests
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.file_config import ALLOWED_EXTENSIONS, UPLOAD_DIR, MAX_FILE_SIZE, MAX_EXTRACTED_TEXT
from app.services.document_parser import DocumentParser
from app.utils.file_utils import validate_mime, delete_file

router = APIRouter()
parser = DocumentParser()
logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL if REDIS_URL else None
)

# Rate limit: 10 uploads per minute per IP Address

# File upload endpoint
@router.post("/upload-file")
@limiter.limit("10/minute")
async def upload_file(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_path = None

    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Invalid file name")

        logger.info(f"Upload started: {file.filename}")

        # Extension check
        ext = Path(file.filename).suffix.lower().replace(".", "")
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}",
            )

        # write uploaded file to disk in chunks with size validation
        safe_name = Path(file.filename).name
        unique_name = f"{uuid.uuid4()}_{safe_name}"
        file_path = UPLOAD_DIR / unique_name

        total_bytes = 0

        try:
            with open(file_path, "wb") as buffer:
                # read the file in 1 MB chunks to avoid loading large files into memory
                while chunk := await file.read(1024 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > MAX_FILE_SIZE:
                        raise HTTPException(
                            status_code=400,
                            detail="File too large (max 10 MB)",
                        )
                    buffer.write(chunk)

        except HTTPException:
            raise

        except Exception:
            logger.exception("Error while streaming file")
            raise HTTPException(
                status_code=400,
                detail="Failed to process uploaded file",
            )

        # Empty file check
        if total_bytes == 0:
            logger.warning(f"Empty file uploaded: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty",
            )

        logger.info(f"File saved ({total_bytes} bytes): {file_path}")
        # MIME type validation using magic bytes
        validate_mime(file_path, ext)
        text = await asyncio.to_thread(
            parser.parse_file, str(file_path), file.filename
        )
        logger.info(f"Parsing completed: {file.filename}")
        if not text or not text.strip():
            logger.warning(f"No extractable content from file: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="No extractable content found in file",
            )

        if len(text) > MAX_EXTRACTED_TEXT:
            raise HTTPException(
                status_code=400,
                detail=f"Extracted text too large ({len(text):,} chars). "
                       "Please upload a smaller document.",
            )

        background_tasks.add_task(delete_file, file_path)

        return {
            "status": "success",
            "type": "file",
            "filename": file.filename,
            "message": "File parsed successfully",
            "preview": text[:500],
            "length": len(text),
        }

    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        if file_path:
            delete_file(file_path)
        raise HTTPException(status_code=400, detail=str(ve))

    except HTTPException:
        if file_path:
            delete_file(file_path)
        raise

    except Exception:
        logger.exception("File upload failed")
        if file_path:
            delete_file(file_path)
        raise HTTPException(status_code=500, detail="Internal server error")


# URL upload endpoint
@router.post("/upload-url")
@limiter.limit("10/minute")
async def upload_url(request: Request, background_tasks: BackgroundTasks, url: str = Form(...)):
    try:
        url = url.strip() if url else None

        if not url:
            raise HTTPException(status_code=400, detail="URL cannot be empty")

        logger.info(f"URL upload started: {url}")

        # Auto-add scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)

        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL")

        # Strict domain validation
        netloc_host = parsed.hostname or ""
        parts = netloc_host.split(".")
        if len(parts) < 2 or any(len(p) == 0 for p in parts):
            raise HTTPException(status_code=400, detail="Invalid domain")

        headers = {"User-Agent": "Mozilla/5.0"}

        try:
            response = await asyncio.to_thread(
                requests.get, url, headers=headers, timeout=(3,8)
            )
            response.raise_for_status()

        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, "status_code", "unknown")
            logger.warning(f"URL inaccessible: {url} : status {status}")
            raise HTTPException(
                status_code=400,
                detail=f"URL not accessible (status {status})",
            )

        except requests.exceptions.RequestException:
            logger.error(f"Network error fetching URL: {url}")
            raise HTTPException(
                status_code=400,
                detail="Failed to reach URL (network issue)",
            )

        # Content-Type validation
        content_type = response.headers.get("content-type", "").lower()

        if "text" not in content_type and "html" not in content_type:
            logger.warning(f"Unsupported content-type: {content_type} for URL: {url}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type: {content_type}. Only text-based pages are allowed.",
            )

        if not response.text or len(response.text.strip()) == 0:
            logger.warning(f"Empty response body from URL: {url}")
            raise HTTPException(
                status_code=400,
                detail="Empty response body — nothing to extract",
            )

        # Parsing the URL content
        text = await asyncio.to_thread(
            parser.parse_url_from_content, response.text, url
        )

        if not text or not text.strip():
            logger.warning(f"No content extracted from: {url}")
            raise HTTPException(
                status_code=400,
                detail="No extractable content found (possibly JS-heavy or blocked site)",
            )

        if len(text) > MAX_EXTRACTED_TEXT:
            raise HTTPException(
                status_code=400,
                detail=f"Extracted text too large ({len(text):,} chars). Try a more specific page.",
            )

        logger.info(f"URL parsed successfully: {url}")

        return {
            "status": "success",
            "type": "url",
            "url": url,
            "message": "URL parsed successfully",
            "preview": text[:500],
            "length": len(text),
        }

    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))

    except HTTPException:
        raise

    except Exception:
        logger.exception("URL processing failed")
        raise HTTPException(status_code=500, detail="Internal server error")
