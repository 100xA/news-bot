"""Simple curses-based menu for the news reader."""

import asyncio
import curses
import textwrap
import webbrowser

from .cache import ArticleCache
from .config import Config
from .extractor import ArticleExtractor
from .fetcher import FeedFetcher
from .models import Article, Country, Source

# Minimum terminal size
MIN_WIDTH = 40
MIN_HEIGHT = 10


class Menu:
    """Simple curses-based menu interface."""
    
    def __init__(self, config: Config, force_refresh: bool = False):
        """Initialize the menu."""
        self.config = config
        self.force_refresh = force_refresh
        self.cache = ArticleCache(expiry_hours=config.cache_expiry_hours)
        self.extractor = ArticleExtractor(self.cache)
        
        self._articles: list[Article] = []
        self._source_names: dict[str, str] = {}
        self._stdscr = None
    
    def run(self) -> None:
        """Run the menu interface."""
        curses.wrapper(self._main)
    
    def _main(self, stdscr) -> None:
        """Main curses loop."""
        self._stdscr = stdscr
        curses.curs_set(0)  # Hide cursor
        stdscr.clear()
        stdscr.nodelay(False)  # Blocking input
        
        # Setup colors if available
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)    # Headers
            curses.init_pair(2, curses.COLOR_GREEN, -1)   # Selected
            curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Unread marker
            curses.init_pair(4, 8, -1)                    # Dim (gray)
        
        # Build source names lookup
        for source in self.config.sources:
            self._source_names[source.id] = source.name
        
        # Load articles
        self._show_loading("Fetching news feeds...")
        asyncio.run(self._load_articles())
        
        # Show source selection
        self._source_menu()
    
    def _get_size(self) -> tuple[int, int]:
        """Get terminal size, handling resize."""
        h, w = self._stdscr.getmaxyx()
        return max(h, MIN_HEIGHT), max(w, MIN_WIDTH)
    
    def _safe_addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        """Safely add string, handling edge cases."""
        h, w = self._get_size()
        if y < 0 or y >= h or x < 0:
            return
        # Truncate text to fit
        max_len = w - x - 1
        if max_len <= 0:
            return
        try:
            self._stdscr.addstr(y, x, text[:max_len], attr)
        except curses.error:
            pass
    
    def _show_loading(self, message: str) -> None:
        """Show a loading message."""
        self._stdscr.clear()
        h, w = self._get_size()
        y = h // 2
        x = max(0, (w - len(message)) // 2)
        self._safe_addstr(y, x, message)
        self._stdscr.refresh()
    
    async def _load_articles(self) -> None:
        """Load articles from all sources."""
        async with FeedFetcher(self.cache) as fetcher:
            results = await fetcher.fetch_all_sources(
                self.config.sources,
                force_refresh=self.force_refresh,
            )
        
        # Combine all articles
        all_articles = []
        for articles in results.values():
            all_articles.extend(articles)
        
        # Sort by date
        all_articles.sort(
            key=lambda a: a.published or a.fetched_at,
            reverse=True
        )
        
        self._articles = all_articles
    
    def _build_source_items(self) -> list[tuple[str, Source | str | None]]:
        """Build the source menu items list."""
        items: list[tuple[str, Source | str | None]] = [("All Sources", None)]
        
        # Group by country - order matters
        by_country = self.config.get_sources_by_country()
        order = [
            Country.JAPAN, 
            Country.SOUTH_KOREA, 
            Country.CHINA,
            Country.POLAND,
            Country.GERMANY,
            Country.ACADEMIC,
            Country.FINANCE,
            Country.REGIONAL,
        ]
        
        country_codes = {
            Country.JAPAN: "[JP]",
            Country.SOUTH_KOREA: "[KR]",
            Country.CHINA: "[CN]",
            Country.POLAND: "[PL]",
            Country.GERMANY: "[DE]",
            Country.ACADEMIC: "[Ac]",
            Country.FINANCE: "[$$]",
            Country.REGIONAL: "[--]",
        }
        
        for country in order:
            if country in by_country:
                prefix = country_codes.get(country, "")
                items.append((f"--- {prefix} {country.value} ---", "header"))
                for source in by_country[country]:
                    count = len([a for a in self._articles if a.source_id == source.id])
                    items.append((f"{source.name} ({count})", source))
        
        return items
    
    def _source_menu(self) -> None:
        """Display source selection menu."""
        items = self._build_source_items()
        selected = 0
        
        while True:
            self._draw_source_menu(items, selected)
            
            key = self._stdscr.getch()
            
            if key == curses.KEY_RESIZE:
                self._stdscr.clear()
                continue
            elif key == ord('q'):
                return
            elif key == ord('r'):
                self._show_loading("Refreshing feeds...")
                self.force_refresh = True
                asyncio.run(self._load_articles())
                self.force_refresh = False
                items = self._build_source_items()
            elif key == curses.KEY_UP or key == ord('k'):
                selected = self._move_selection(items, selected, -1)
            elif key == curses.KEY_DOWN or key == ord('j'):
                selected = self._move_selection(items, selected, 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                item = items[selected]
                if item[1] != "header":
                    self._article_menu(item[1] if isinstance(item[1], Source) else None)
    
    def _move_selection(self, items: list, current: int, direction: int) -> int:
        """Move selection, skipping headers."""
        new_pos = current + direction
        while 0 <= new_pos < len(items):
            if items[new_pos][1] != "header":
                return new_pos
            new_pos += direction
        return current
    
    def _draw_source_menu(self, items: list, selected: int) -> None:
        """Draw the source selection menu."""
        self._stdscr.clear()
        h, w = self._get_size()
        
        # Header
        title = "NEWS READER"
        self._safe_addstr(0, (w - len(title)) // 2, title,
                         curses.color_pair(1) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD)
        self._safe_addstr(1, 0, "=" * (w - 1))
        
        # Calculate scroll offset
        max_visible = h - 6
        if max_visible < 1:
            max_visible = 1
        scroll_offset = max(0, selected - max_visible + 3)
        
        # Draw items
        y = 3
        for i, (label, value) in enumerate(items[scroll_offset:]):
            if y >= h - 3:
                break
            
            actual_idx = i + scroll_offset
            is_selected = actual_idx == selected
            is_header = value == "header"
            
            if is_header:
                attr = curses.color_pair(4) if curses.has_colors() else curses.A_DIM
                self._safe_addstr(y, 0, f"   {label}", attr)
            else:
                prefix = " > " if is_selected else "   "
                attr = 0
                if is_selected and curses.has_colors():
                    attr = curses.color_pair(2) | curses.A_BOLD
                elif is_selected:
                    attr = curses.A_REVERSE
                self._safe_addstr(y, 0, f"{prefix}{label}", attr)
            
            y += 1
        
        # Footer
        footer = "j/k:move Enter:select r:refresh q:quit"
        self._safe_addstr(h - 2, 0, "-" * (w - 1))
        self._safe_addstr(h - 1, 0, footer)
        
        self._stdscr.refresh()
    
    def _article_menu(self, source: Source | None) -> None:
        """Display article list for a source."""
        if source is None:
            articles = self._articles[:100]
            title = "All Sources"
        else:
            articles = [a for a in self._articles if a.source_id == source.id]
            title = source.name
        
        if not articles:
            return
        
        selected = 0
        
        while True:
            self._draw_article_menu(articles, selected, title)
            
            key = self._stdscr.getch()
            
            if key == curses.KEY_RESIZE:
                self._stdscr.clear()
                continue
            elif key == ord('q') or key == ord('b') or key == 27:
                return
            elif key == curses.KEY_UP or key == ord('k'):
                selected = max(0, selected - 1)
            elif key == curses.KEY_DOWN or key == ord('j'):
                selected = min(len(articles) - 1, selected + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                self._read_article(articles[selected])
            elif key == ord('o'):
                if articles[selected].url:
                    webbrowser.open(articles[selected].url)
    
    def _draw_article_menu(self, articles: list[Article], selected: int, title: str) -> None:
        """Draw the article list menu."""
        self._stdscr.clear()
        h, w = self._get_size()
        
        # Header
        header = f"{title} ({len(articles)})"
        self._safe_addstr(0, 0, header,
                         curses.color_pair(1) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD)
        self._safe_addstr(1, 0, "=" * min(w - 1, len(header) + 4))
        
        # Calculate scroll offset
        max_visible = h - 6
        if max_visible < 1:
            max_visible = 1
        scroll_offset = max(0, selected - max_visible + 3)
        
        # Draw articles
        y = 3
        for i, article in enumerate(articles[scroll_offset:]):
            if y >= h - 3:
                break
            
            actual_idx = i + scroll_offset
            is_selected = actual_idx == selected
            
            # Build line parts
            marker = "* " if not article.is_read else "  "
            prefix = " > " if is_selected else "   "
            
            # Source name if showing all
            source_tag = ""
            if title == "All Sources":
                sname = self._source_names.get(article.source_id, "")
                if sname:
                    source_tag = f"[{sname[:8]}] "
            
            # Date
            date_str = f" ({article.display_date})" if article.display_date else ""
            
            # Calculate available space for title
            fixed_len = len(prefix) + len(marker) + len(source_tag) + len(date_str)
            max_title = w - fixed_len - 2
            if max_title < 10:
                max_title = 10
            
            article_title = article.title[:max_title]
            line = f"{prefix}{marker}{source_tag}{article_title}{date_str}"
            
            # Attributes
            attr = 0
            if is_selected and curses.has_colors():
                attr = curses.color_pair(2) | curses.A_BOLD
            elif is_selected:
                attr = curses.A_REVERSE
            elif not article.is_read and curses.has_colors():
                attr = curses.color_pair(3)
            
            self._safe_addstr(y, 0, line, attr)
            y += 1
        
        # Footer
        footer = "j/k:move Enter:read o:browser b:back q:quit"
        self._safe_addstr(h - 2, 0, "-" * (w - 1))
        self._safe_addstr(h - 1, 0, footer)
        
        self._stdscr.refresh()
    
    def _read_article(self, article: Article) -> None:
        """Display full article content."""
        # Mark as read
        self.cache.mark_as_read(article.id)
        article.is_read = True
        
        # Show loading
        self._show_loading("Loading article...")
        
        # Extract content
        content = asyncio.run(self.extractor.extract_article(article))
        
        # Display article
        self._display_article(article, content)
    
    def _build_article_lines(self, article: Article, content: str, width: int) -> list[str]:
        """Build wrapped lines for article display."""
        lines = []
        wrap_width = max(20, width - 2)
        
        # Title (may wrap)
        for line in textwrap.wrap(article.title, width=wrap_width):
            lines.append(line)
        lines.append("")
        
        # Meta
        meta_parts = []
        if article.author:
            meta_parts.append(f"By {article.author}")
        if article.display_date:
            meta_parts.append(article.display_date)
        if meta_parts:
            lines.append(" | ".join(meta_parts))
            lines.append("")
        
        lines.append("-" * min(50, wrap_width))
        lines.append("")
        
        # Content with word wrap
        text = content or article.summary or "No content available"
        for paragraph in text.split("\n"):
            if paragraph.strip():
                wrapped = textwrap.wrap(paragraph, width=wrap_width)
                lines.extend(wrapped)
                lines.append("")
            else:
                lines.append("")
        
        lines.append("-" * min(50, wrap_width))
        lines.append(f"URL: {article.url}"[:wrap_width])
        
        return lines
    
    def _display_article(self, article: Article, content: str) -> None:
        """Display article content with scrolling."""
        scroll_offset = 0
        
        while True:
            h, w = self._get_size()
            lines = self._build_article_lines(article, content, w)
            max_scroll = max(0, len(lines) - (h - 4))
            scroll_offset = min(scroll_offset, max_scroll)
            
            self._stdscr.clear()
            
            # Draw content
            for i, line in enumerate(lines[scroll_offset:]):
                if i >= h - 3:
                    break
                attr = curses.A_BOLD if i == 0 and scroll_offset == 0 else 0
                self._safe_addstr(i, 0, line, attr)
            
            # Footer with scroll position
            if max_scroll > 0:
                pct = int((scroll_offset / max_scroll) * 100) if max_scroll > 0 else 100
                footer = f"j/k:scroll o:browser b:back [{pct}%]"
            else:
                footer = "o:browser b:back q:quit"
            
            self._safe_addstr(h - 2, 0, "-" * (w - 1))
            self._safe_addstr(h - 1, 0, footer)
            
            self._stdscr.refresh()
            
            key = self._stdscr.getch()
            
            if key == curses.KEY_RESIZE:
                self._stdscr.clear()
                continue
            elif key == ord('q') or key == ord('b') or key == 27:
                return
            elif key == curses.KEY_UP or key == ord('k'):
                scroll_offset = max(0, scroll_offset - 1)
            elif key == curses.KEY_DOWN or key == ord('j'):
                scroll_offset = min(max_scroll, scroll_offset + 1)
            elif key == curses.KEY_PPAGE:
                scroll_offset = max(0, scroll_offset - (h - 4))
            elif key == curses.KEY_NPAGE:
                scroll_offset = min(max_scroll, scroll_offset + (h - 4))
            elif key == ord('o'):
                if article.url:
                    webbrowser.open(article.url)


def run_menu(config: Config | None = None, force_refresh: bool = False) -> None:
    """Run the menu interface."""
    config = config or Config()
    menu = Menu(config, force_refresh)
    menu.run()
