"""Command-line interface for the news reader."""

import argparse
import sys

from .config import Config
from .menu import run_menu


def print_headlines(config: Config, limit: int = 20) -> None:
    """Print headlines to stdout (non-interactive mode)."""
    from .cache import ArticleCache
    from .fetcher import FeedFetcher
    import asyncio
    
    cache = ArticleCache(expiry_hours=config.cache_expiry_hours)
    
    async def fetch_and_print():
        async with FeedFetcher(cache) as fetcher:
            print("Fetching news feeds...", file=sys.stderr)
            results = await fetcher.fetch_all_sources(config.sources)
        
        # Combine and sort articles
        all_articles = []
        source_names = {s.id: s.name for s in config.sources}
        
        for articles in results.values():
            all_articles.extend(articles)
        
        all_articles.sort(
            key=lambda a: a.published or a.fetched_at,
            reverse=True
        )
        
        print()
        print("=" * 60)
        print("  EAST ASIAN NEWS HEADLINES")
        print("=" * 60)
        print()
        
        current_source = None
        count = 0
        
        for article in all_articles[:limit]:
            if count >= limit:
                break
            
            source_name = source_names.get(article.source_id, "Unknown")
            
            # Print source header if changed
            if source_name != current_source:
                if current_source is not None:
                    print()
                print(f"  [{source_name}]")
                current_source = source_name
            
            # Print article
            date_str = article.display_date
            date_suffix = f" ({date_str})" if date_str else ""
            print(f"    - {article.title[:70]}{date_suffix}")
            count += 1
        
        print()
        print("-" * 60)
        print(f"  Showing {count} articles from {len(config.sources)} sources")
        print("  Run 'news' for interactive mode")
        print("-" * 60)
    
    asyncio.run(fetch_and_print())


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="news",
        description="East Asian News Terminal Reader",
        epilog="Run without arguments for interactive mode.",
    )
    
    parser.add_argument(
        "--refresh", "-r",
        action="store_true",
        help="Force refresh all feeds (ignore cache)",
    )
    
    parser.add_argument(
        "--headlines", "-H",
        action="store_true",
        help="Print headlines only (non-interactive)",
    )
    
    parser.add_argument(
        "--startup", "-s",
        action="store_true",
        help="Startup mode: print brief summary and exit",
    )
    
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=20,
        help="Number of headlines to show (default: 20)",
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to config file",
    )
    
    args = parser.parse_args()
    
    # Load config
    from pathlib import Path
    config_path = Path(args.config) if args.config else None
    config = Config(config_path)
    
    if not config.sources:
        print("Error: No news sources configured.", file=sys.stderr)
        print("Please check your config.yaml file.", file=sys.stderr)
        sys.exit(1)
    
    # Run appropriate mode
    if args.headlines or args.startup:
        limit = 10 if args.startup else args.limit
        print_headlines(config, limit=limit)
    else:
        run_menu(
            config=config,
            force_refresh=args.refresh,
        )


if __name__ == "__main__":
    main()
