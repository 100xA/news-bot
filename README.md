# East Asian News Terminal Reader

An interactive terminal-based news reader for East Asian news sources (Japan, South Korea, China).

## Features

- **14 Free News Sources** from Japan, Korea, China, and regional outlets
- **Simple Arrow-Key Menu** for easy navigation
- **Full Article Reader** with content extraction
- **Smart Caching** for offline reading
- **Async Fetching** for fast loading
- **Configurable** sources and settings

## Installation

### With uv (recommended)

```bash
# Clone or navigate to the project
cd news-bot

# Install with uv
uv sync

# Run the app
uv run news
```

### Install globally

```bash
# Install as a tool
uv tool install .

# Now you can run from anywhere
news
```

## Usage

### Interactive Mode (default)

```bash
news                    # Launch interactive menu
news --refresh          # Force refresh all feeds
```

### Headlines Only

```bash
news --headlines        # Print headlines and exit
news -H -n 30           # Show 30 headlines
```

### Startup Mode

```bash
news --startup          # Brief summary (10 headlines)
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `j` / Down | Move down |
| `k` / Up | Move up |
| `Enter` | Select item |
| `o` | Open in browser |
| `r` | Refresh feeds |
| `b` | Go back |
| `q` | Quit |
| `Page Up/Dn` | Scroll article |

## Shell Integration

### Auto-run on Terminal Startup

Add to your `~/.zshrc` (or `~/.bashrc`):

```bash
# Show news headlines on new terminal
news --startup
```

Or for interactive mode:

```bash
# Launch news reader on startup (uncomment to enable)
# news
```

### Alias Shortcuts

```bash
# Add to ~/.zshrc
alias n='news'
alias nh='news --headlines'
alias nr='news --refresh'
```

## Configuration

The config file is searched in this order:
1. `./config.yaml` (current directory)
2. `~/.config/news-bot/config.yaml`
3. `~/.news-bot/config.yaml`

### Example Config

```yaml
cache:
  expiry_hours: 24
  max_articles_per_source: 50

sources:
  - id: nhk_world
    name: NHK World
    country: Japan
    url: https://www3.nhk.or.jp/nhkworld/en/news/
    rss_url: https://www3.nhk.or.jp/rss/news/cat0.xml
    enabled: true
```

### Disabling Sources

Set `enabled: false` for any source you want to skip:

```yaml
  - id: xinhua
    name: Xinhua
    ...
    enabled: false  # Won't fetch this source
```

## Included Sources

### Japan
- NHK World
- Kyodo News
- The Mainichi
- The Japan News
- Japan Today

### South Korea
- Yonhap News
- The Korea Herald
- The Korea Times
- Korea JoongAng Daily

### China
- Xinhua
- CGTN
- People's Daily
- China Daily

### Regional
- The Diplomat

## Data Storage

- **Cache**: `~/.local/share/news-bot/articles.db`
- **Config**: See Configuration section above

## Development

```bash
# Clone the repo
git clone <repo-url>
cd news-bot

# Install dependencies
uv sync

# Run in development
uv run news

# Run tests (if any)
uv run pytest
```

## License

MIT
