from typing import List, Optional
from pydantic import BaseModel, Field


class QARequest(BaseModel):
    query:  str        = Field(..., min_length=1)
    top_k:  int        = Field(default=5, ge=1, le=20)


class QueryRequest(BaseModel):
    query:  str        = Field(..., min_length=1)
    top_k:  int        = Field(default=5, ge=1, le=20)


class ProcessNewsRequest(BaseModel):
    urls: Optional[List[str]] = None
