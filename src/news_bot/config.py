"""Configuration loader for the news reader."""

import os
from pathlib import Path

import yaml

from .models import Country, Source


DEFAULT_CONFIG = {
    "cache": {
        "expiry_hours": 24,
        "max_articles_per_source": 50,
    },
    "sources": [],
}


def get_config_path() -> Path:
    """Get the path to the config file."""
    # Check for config in current directory first
    local_config = Path.cwd() / "config.yaml"
    if local_config.exists():
        return local_config
    
    # Check in XDG config directory
    xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    xdg_config_path = xdg_config / "news-bot" / "config.yaml"
    if xdg_config_path.exists():
        return xdg_config_path
    
    # Check in home directory
    home_config = Path.home() / ".news-bot" / "config.yaml"
    if home_config.exists():
        return home_config
    
    # Fall back to package directory
    package_config = Path(__file__).parent.parent.parent.parent / "config.yaml"
    if package_config.exists():
        return package_config
    
    return local_config  # Will create here if needed


def get_data_dir() -> Path:
    """Get the data directory for cache and database."""
    xdg_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    data_dir = xdg_data / "news-bot"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class Config:
    """Configuration manager for the news reader."""
    
    def __init__(self, config_path: Path | None = None):
        """Initialize configuration."""
        self.config_path = config_path or get_config_path()
        self._config = self._load_config()
        self._sources: list[Source] | None = None
    
    def _load_config(self) -> dict:
        """Load configuration from file."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
                return {**DEFAULT_CONFIG, **config} if config else DEFAULT_CONFIG
        return DEFAULT_CONFIG
    
    @property
    def cache_expiry_hours(self) -> int:
        """Get cache expiry in hours."""
        return self._config.get("cache", {}).get("expiry_hours", 24)
    
    @property
    def max_articles_per_source(self) -> int:
        """Get maximum articles to keep per source."""
        return self._config.get("cache", {}).get("max_articles_per_source", 50)
    
    @property
    def sources(self) -> list[Source]:
        """Get list of enabled news sources."""
        if self._sources is None:
            self._sources = []
            for source_data in self._config.get("sources", []):
                try:
                    source = Source.from_dict(source_data)
                    if source.enabled:
                        self._sources.append(source)
                except (KeyError, ValueError) as e:
                    print(f"Warning: Invalid source config: {e}")
        return self._sources
    
    def get_sources_by_country(self) -> dict[Country, list[Source]]:
        """Get sources grouped by country."""
        grouped: dict[Country, list[Source]] = {}
        for source in self.sources:
            if source.country not in grouped:
                grouped[source.country] = []
            grouped[source.country].append(source)
        return grouped
    
    def get_source_by_id(self, source_id: str) -> Source | None:
        """Get a source by its ID."""
        for source in self.sources:
            if source.id == source_id:
                return source
        return None
