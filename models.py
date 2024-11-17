from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

class GovPageDetails(BaseModel):
    body: Optional[str] = None
    external_related_links: List[Any] = []
    current: Optional[bool] = None
    ended_on: Optional[str] = None
    parts: Optional[List[Any]] = None

class GovPageLink(BaseModel):
    title: str
    base_path: str
    api_path: str
    web_url: str
    locale: str = "en"

class GovPageLinks(BaseModel):
    organisations: Optional[List[GovPageLink]] = []
    parent: Optional[List[GovPageLink]] = []
    available_translations: Optional[List[GovPageLink]] = []

class Snippet(BaseModel):
    well_written_snippet: str
    badly_written_snippet: str

class ArticleSnippets(BaseModel):
    snippets: List[Snippet]

class SyntheticData(BaseModel):
    poorly_written_article: str
    article_snippets: Optional[ArticleSnippets] = None

class GovPage(BaseModel):
    title: str
    base_path: str
    content_id: str
    description: Optional[str] = None
    document_type: str
    schema_name: str
    locale: str = "en"
    api_path: Optional[str] = None
    web_url: Optional[str] = None
    details: GovPageDetails
    links: GovPageLinks
    public_updated_at: Optional[datetime] = None
    first_published_at: Optional[datetime] = None
    withdrawn: bool = False
    synthetic_data: Optional[SyntheticData] = None 