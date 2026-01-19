"""Full article content extraction using trafilatura."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import httpx
import trafilatura

from .cache import ArticleCache
from .models import Article


class ArticleExtractor:
    """Extract full article content from URLs."""
    
    def __init__(self, cache: ArticleCache, timeout: float = 30.0):
        """Initialize the extractor."""
        self.cache = cache
        self.timeout = timeout
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    def _extract_content(self, html: str, url: str) -> str:
        """Extract main content from HTML using trafilatura."""
        try:
            content = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
            )
            return content or ""
        except Exception:
            return ""
    
    async def extract_article(
        self, 
        article: Article,
        force_refresh: bool = False
    ) -> str:
        """Extract full content for an article."""
        # Return cached content if available
        if article.content and not force_refresh:
            return article.content
        
        # Check cache for updated content
        cached = self.cache.get_article(article.id)
        if cached and cached.content and not force_refresh:
            return cached.content
        
        if not article.url:
            return article.summary
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                }
            ) as client:
                response = await client.get(article.url)
                response.raise_for_status()
                html = response.text
            
            # Run trafilatura in thread pool (it's CPU-bound)
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self._executor,
                self._extract_content,
                html,
                article.url
            )
            
            if content:
                # Update cache with extracted content
                self.cache.update_content(article.id, content)
                return content
            
            return article.summary
            
        except httpx.HTTPError:
            return article.summary
        except Exception:
            return article.summary
    
    async def extract_multiple(
        self, 
        articles: list[Article],
        on_progress: callable | None = None,
    ) -> dict[str, str]:
        """Extract content for multiple articles concurrently."""
        results: dict[str, str] = {}
        
        async def extract_with_progress(article: Article) -> tuple[str, str]:
            content = await self.extract_article(article)
            if on_progress:
                on_progress(article)
            return article.id, content
        
        # Limit concurrency to avoid overwhelming servers
        semaphore = asyncio.Semaphore(5)
        
        async def extract_limited(article: Article) -> tuple[str, str]:
            async with semaphore:
                return await extract_with_progress(article)
        
        tasks = [extract_limited(article) for article in articles]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed:
            if isinstance(result, tuple):
                article_id, content = result
                results[article_id] = content
        
        return results
    
    def shutdown(self) -> None:
        """Shutdown the thread pool executor."""
        self._executor.shutdown(wait=False)
