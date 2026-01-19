"""Data models for the news reader."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Country(Enum):
    """Country/region for news sources."""
    
    JAPAN = "Japan"
    SOUTH_KOREA = "South Korea"
    CHINA = "China"
    POLAND = "Poland"
    GERMANY = "Germany"
    ACADEMIC = "Academic"
    REGIONAL = "Regional"


@dataclass
class Source:
    """A news source configuration."""
    
    id: str
    name: str
    country: Country
    url: str
    rss_url: str
    enabled: bool = True
    
    @classmethod
    def from_dict(cls, data: dict) -> "Source":
        """Create a Source from a dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            country=Country(data["country"]),
            url=data["url"],
            rss_url=data["rss_url"],
            enabled=data.get("enabled", True),
        )


@dataclass
class Article:
    """A news article."""
    
    id: str
    source_id: str
    title: str
    url: str
    summary: str = ""
    content: str = ""
    author: str = ""
    published: datetime | None = None
    fetched_at: datetime = field(default_factory=datetime.now)
    is_read: bool = False
    
    @property
    def display_date(self) -> str:
        """Get a formatted date string for display."""
        if self.published:
            now = datetime.now()
            diff = now - self.published
            
            if diff.days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    minutes = diff.seconds // 60
                    return f"{minutes}m ago" if minutes > 0 else "just now"
                return f"{hours}h ago"
            elif diff.days == 1:
                return "yesterday"
            elif diff.days < 7:
                return f"{diff.days}d ago"
            else:
                return self.published.strftime("%b %d")
        return ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "content": self.content,
            "author": self.author,
            "published": self.published.isoformat() if self.published else None,
            "fetched_at": self.fetched_at.isoformat(),
            "is_read": self.is_read,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create an Article from a dictionary."""
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            title=data["title"],
            url=data["url"],
            summary=data.get("summary", ""),
            content=data.get("content", ""),
            author=data.get("author", ""),
            published=datetime.fromisoformat(data["published"]) if data.get("published") else None,
            fetched_at=datetime.fromisoformat(data["fetched_at"]) if data.get("fetched_at") else datetime.now(),
            is_read=data.get("is_read", False),
        )
