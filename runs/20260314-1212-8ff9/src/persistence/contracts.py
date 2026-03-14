from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ArticleBase(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=2000)
    url: HttpUrl
    published_at: datetime | None = None
    scraped_at: datetime | None = None
    section: str = ""
    author: str = ""
    summary: str = ""
    article_text: str = ""
    tags: str = ""


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: str | None = None
    published_at: datetime | None = None
    scraped_at: datetime | None = None
    section: str | None = None
    author: str | None = None
    summary: str | None = None
    article_text: str | None = None
    tags: str | None = None


class ArticleRead(ArticleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ArticleDelete(BaseModel):
    source: str
    url: HttpUrl


class IngestResult(BaseModel):
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: int = 0
