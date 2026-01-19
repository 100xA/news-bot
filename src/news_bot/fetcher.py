"""RSS feed fetcher for news sources."""

import asyncio
import hashlib
from datetime import datetime
from time import mktime

import feedparser
import httpx

from .cache import ArticleCache
from .models import Article, Source


class FeedFetcher:
    """Async RSS feed fetcher."""
    
    def __init__(self, cache: ArticleCache, timeout: float = 30.0):
        """Initialize the fetcher."""
        self.cache = cache
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
    
    async def __aenter__(self) -> "FeedFetcher":
        """Enter async context."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "NewsBot/1.0 (Terminal News Reader)"
            }
        )
        return self
    
    async def __aexit__(self, *args) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _generate_article_id(self, source_id: str, url: str, title: str) -> str:
        """Generate a unique article ID."""
        content = f"{source_id}:{url}:{title}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _parse_date(self, entry: dict) -> datetime | None:
        """Parse date from feed entry."""
        for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
            if date_field in entry and entry[date_field]:
                try:
                    return datetime.fromtimestamp(mktime(entry[date_field]))
                except (TypeError, ValueError, OverflowError):
                    continue
        return None
    
    def _entry_to_article(self, entry: dict, source: Source) -> Article:
        """Convert a feed entry to an Article."""
        url = entry.get("link", "")
        title = entry.get("title", "No title")
        
        # Get summary/description
        summary = ""
        if "summary" in entry:
            summary = entry["summary"]
        elif "description" in entry:
            summary = entry["description"]
        
        # Strip HTML tags from summary (basic)
        import re
        summary = re.sub(r"<[^>]+>", "", summary)
        summary = summary.strip()[:500]  # Limit summary length
        
        # Get author
        author = ""
        if "author" in entry:
            author = entry["author"]
        elif "authors" in entry and entry["authors"]:
            author = entry["authors"][0].get("name", "")
        
        return Article(
            id=self._generate_article_id(source.id, url, title),
            source_id=source.id,
            title=title,
            url=url,
            summary=summary,
            author=author,
            published=self._parse_date(entry),
            fetched_at=datetime.now(),
        )
    
    async def fetch_source(
        self, 
        source: Source, 
        force_refresh: bool = False
    ) -> list[Article]:
        """Fetch articles from a single source."""
        # Check if we have fresh data and don't need to refresh
        if not force_refresh and self.cache.is_fresh(source.id):
            return self.cache.get_articles_by_source(source.id)
        
        if not self._client:
            raise RuntimeError("Fetcher must be used as async context manager")
        
        try:
            response = await self._client.get(source.rss_url)
            response.raise_for_status()
            
            feed = feedparser.parse(response.text)
            
            if feed.bozo and not feed.entries:
                # Feed parsing error and no entries
                return self.cache.get_articles_by_source(source.id)
            
            articles = []
            for entry in feed.entries[:50]:  # Limit to 50 entries
                try:
                    article = self._entry_to_article(entry, source)
                    articles.append(article)
                except Exception:
                    continue
            
            if articles:
                self.cache.save_articles(articles)
            
            return articles
            
        except httpx.HTTPError:
            # Return cached articles on error
            return self.cache.get_articles_by_source(source.id)
        except Exception:
            return self.cache.get_articles_by_source(source.id)
    
    async def fetch_all_sources(
        self, 
        sources: list[Source],
        force_refresh: bool = False,
        on_progress: callable | None = None,
    ) -> dict[str, list[Article]]:
        """Fetch articles from all sources concurrently."""
        results: dict[str, list[Article]] = {}
        
        async def fetch_with_progress(source: Source) -> tuple[str, list[Article]]:
            articles = await self.fetch_source(source, force_refresh)
            if on_progress:
                on_progress(source, len(articles))
            return source.id, articles
        
        tasks = [fetch_with_progress(source) for source in sources]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed:
            if isinstance(result, tuple):
                source_id, articles = result
                results[source_id] = articles
            # Skip exceptions, they return cached data
        
        return results
    
    async def fetch_article_content(self, article: Article) -> str:
        """Fetch full article content (placeholder for extractor)."""
        # This will be implemented in the extractor module
        return article.content or article.summary
