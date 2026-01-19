# News Terminal Reader

An interactive terminal-based news reader for international news sources and arXiv papers.

## Features

- **17 Free News Sources** from Japan, Korea, China, Poland, Germany, and arXiv
- **Simple Arrow-Key Menu** with curses-based interface
- **Full Article Reader** with content extraction
- **Smart Caching** with SQLite for offline reading
- **Async Fetching** for fast parallel loading
- **Morning Digest Scheduler** with launchd integration
- **Configurable** sources and settings

## Installation

### With uv (recommended)

```bash
cd news-bot
uv sync
uv run news
```

### Install globally

```bash
uv tool install .
news
```

### Copy config to user directory

```bash
mkdir -p ~/.config/news-bot
cp config.yaml ~/.config/news-bot/
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

## Morning Digest Scheduler

Set up automatic daily news at 8 AM (macOS):

```bash
# Copy the launch agent
cp com.newsbot.morning.plist ~/Library/LaunchAgents/

# Load it
launchctl load ~/Library/LaunchAgents/com.newsbot.morning.plist

# Test it now
launchctl start com.newsbot.morning
```

### Manage the scheduler

```bash
# Check status
launchctl list | grep newsbot

# Disable
launchctl unload ~/Library/LaunchAgents/com.newsbot.morning.plist

# Re-enable
launchctl load ~/Library/LaunchAgents/com.newsbot.morning.plist
```

To change the time, edit the plist and update `Hour`/`Minute` values.

## Shell Integration

Add to your `~/.zshrc`:

```bash
# Quick headlines on terminal startup
news --startup

# Aliases
alias n='news'
alias nh='news --headlines'
alias nr='news --refresh'
```

## Configuration

Config file locations (searched in order):
1. `./config.yaml`
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

```yaml
  - id: some_source
    name: Some Source
    enabled: false  # Won't fetch this source
```

## Included Sources (18 free, no paywalls)

### Japan (English)
- NHK World
- Japan Today

### South Korea (English)
- Yonhap News
- The Korea Herald
- The Korea Times

### China (English)
- China Daily

### Poland (Polish)
- TVN24
- Gazeta.pl
- Onet
- Polsat News

### Germany (German)
- Tagesschau

### arXiv (Academic)
- Computer Science (cs)
- Artificial Intelligence (cs.AI)
- Machine Learning (cs.LG)
- Statistical ML (stat.ML)
- Quantitative Finance (q-fin)

### Finance
- BMO Economics

### Regional (English)
- The Diplomat

## Data Storage

- **Cache**: `~/.local/share/news-bot/articles.db`
- **Config**: `~/.config/news-bot/config.yaml`
- **Scheduler**: `~/Library/LaunchAgents/com.newsbot.morning.plist`

## Development

```bash
git clone <repo-url>
cd news-bot
uv sync
uv run news
```

## License

MIT
