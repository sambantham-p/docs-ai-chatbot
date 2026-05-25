from pydantic import BaseModel
from typing import List, Optional


class ChunkResult(BaseModel):
    chunk_id:      str
    doc_id:        str
    text:          str
    section_title: str | None
    chunk_index:   int
    score:         float


class QueryResponse(BaseModel):
    query:  str
    total:  int
    chunks: list[ChunkResult]


class QAResponse(BaseModel):
    answer:           str
    sources:          list[str]
    confidence:       float = 0.0
    confidence_label: str   = "low"


class UploadResponse(BaseModel):
    status: str
    doc_id: str
    duplicate: bool = False


class ArticleResponse(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    published: Optional[str] = None
    content: Optional[str] = None
    content_source: Optional[str] = None
    source: Optional[str] = None


class FeedResponse(BaseModel):
    feed: str
    count: int
    articles: List[ArticleResponse]


class ProcessNewsResponse(BaseModel):
    total_feeds: int
    total_articles: int
    feeds: List[FeedResponse]



class ExtractedContentResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    source: str = "trafilatura"
    error: Optional[str] = None