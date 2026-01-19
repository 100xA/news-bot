"""SQLite caching layer for articles."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .config import get_data_dir
from .models import Article


class ArticleCache:
    """SQLite-based cache for news articles."""
    
    def __init__(self, db_path: Path | None = None, expiry_hours: int = 24):
        """Initialize the cache."""
        self.db_path = db_path or (get_data_dir() / "articles.db")
        self.expiry_hours = expiry_hours
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    summary TEXT,
                    content TEXT,
                    author TEXT,
                    published TEXT,
                    fetched_at TEXT NOT NULL,
                    is_read INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_source 
                ON articles(source_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_fetched 
                ON articles(fetched_at)
            """)
            conn.commit()
    
    def save_article(self, article: Article) -> None:
        """Save an article to the cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO articles 
                (id, source_id, title, url, summary, content, author, published, fetched_at, is_read)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.id,
                article.source_id,
                article.title,
                article.url,
                article.summary,
                article.content,
                article.author,
                article.published.isoformat() if article.published else None,
                article.fetched_at.isoformat(),
                1 if article.is_read else 0,
            ))
            conn.commit()
    
    def save_articles(self, articles: list[Article]) -> None:
        """Save multiple articles to the cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO articles 
                (id, source_id, title, url, summary, content, author, published, fetched_at, is_read)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    a.id,
                    a.source_id,
                    a.title,
                    a.url,
                    a.summary,
                    a.content,
                    a.author,
                    a.published.isoformat() if a.published else None,
                    a.fetched_at.isoformat(),
                    1 if a.is_read else 0,
                )
                for a in articles
            ])
            conn.commit()
    
    def get_article(self, article_id: str) -> Article | None:
        """Get an article by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM articles WHERE id = ?", (article_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_article(row)
        return None
    
    def get_articles_by_source(
        self, 
        source_id: str, 
        limit: int = 50,
        include_expired: bool = False
    ) -> list[Article]:
        """Get articles for a source."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if include_expired:
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    WHERE source_id = ?
                    ORDER BY published DESC NULLS LAST
                    LIMIT ?
                """, (source_id, limit))
            else:
                cutoff = (datetime.now() - timedelta(hours=self.expiry_hours)).isoformat()
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    WHERE source_id = ? AND fetched_at > ?
                    ORDER BY published DESC NULLS LAST
                    LIMIT ?
                """, (source_id, cutoff, limit))
            
            return [self._row_to_article(row) for row in cursor.fetchall()]
    
    def get_all_articles(
        self, 
        limit: int = 200,
        include_expired: bool = False
    ) -> list[Article]:
        """Get all articles across all sources."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if include_expired:
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    ORDER BY published DESC NULLS LAST
                    LIMIT ?
                """, (limit,))
            else:
                cutoff = (datetime.now() - timedelta(hours=self.expiry_hours)).isoformat()
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    WHERE fetched_at > ?
                    ORDER BY published DESC NULLS LAST
                    LIMIT ?
                """, (cutoff, limit))
            
            return [self._row_to_article(row) for row in cursor.fetchall()]
    
    def mark_as_read(self, article_id: str) -> None:
        """Mark an article as read."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE articles SET is_read = 1 WHERE id = ?", 
                (article_id,)
            )
            conn.commit()
    
    def update_content(self, article_id: str, content: str) -> None:
        """Update the full content of an article."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE articles SET content = ? WHERE id = ?", 
                (content, article_id)
            )
            conn.commit()
    
    def is_fresh(self, source_id: str) -> bool:
        """Check if we have fresh articles for a source."""
        with sqlite3.connect(self.db_path) as conn:
            cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor = conn.execute("""
                SELECT COUNT(*) FROM articles 
                WHERE source_id = ? AND fetched_at > ?
            """, (source_id, cutoff))
            count = cursor.fetchone()[0]
            return count > 0
    
    def cleanup_expired(self) -> int:
        """Remove expired articles. Returns count of deleted articles."""
        cutoff = (datetime.now() - timedelta(hours=self.expiry_hours * 2)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM articles WHERE fetched_at < ?", 
                (cutoff,)
            )
            conn.commit()
            return cursor.rowcount
    
    def _row_to_article(self, row: sqlite3.Row) -> Article:
        """Convert a database row to an Article."""
        return Article(
            id=row["id"],
            source_id=row["source_id"],
            title=row["title"],
            url=row["url"],
            summary=row["summary"] or "",
            content=row["content"] or "",
            author=row["author"] or "",
            published=datetime.fromisoformat(row["published"]) if row["published"] else None,
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            is_read=bool(row["is_read"]),
        )
