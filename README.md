# 🌊 WasteWatch AI

### Automated Wastewater Treatment News Scraper & AI Blog Generator

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat&logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**WasteWatch AI** is a fully automated content pipeline that scrapes the internet for wastewater treatment and pollution incident news, generates professional blog posts using AI (Perplexity Pro), and publishes them to WordPress — all from a beautiful web dashboard.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Scraping** | Automatically scrapes RSS feeds & news sources for wastewater/pollution articles |
| 🤖 **AI Blog Generation** | Uses Perplexity Pro to generate professional, SEO-optimized blog posts |
| 📝 **WordPress Integration** | Publishes directly to WordPress as drafts via REST API |
| 📊 **Web Dashboard** | Beautiful dark-themed dashboard to monitor and control the pipeline |
| ⏰ **Auto Scheduling** | Set-and-forget automation runs on configurable intervals |
| 📄 **HTML Export** | Export blog posts as standalone HTML files for manual upload |
| 🎯 **Relevance Filtering** | Smart keyword matching ensures only relevant articles are processed |
| 💾 **SQLite Database** | No external database needed — everything stored locally |

---

## 🖼️ Dashboard Preview

The dashboard features a premium dark theme with:
- Real-time pipeline statistics
- One-click pipeline controls (Scrape → Generate → Publish)
- Automation scheduler status
- Recent activity feed
- Blog post preview & export

---

## 🚀 Quick Start (Windows / Mac / Linux)

### Prerequisites
- **Python 3.9+** installed ([Download Python](https://www.python.org/downloads/))
- **Perplexity API Key** (optional, works in demo mode without it)
- **WordPress site** with Application Passwords enabled (optional)

### Step 1: Download the Project

```bash
git clone https://github.com/yourusername/wastewatch-ai.git
cd wastewatch-ai
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Settings

```bash
copy .env.example .env       # Windows
# OR
cp .env.example .env         # Mac/Linux
```

Edit `.env` with your settings:

```env
# Required for AI blog generation (optional for demo)
PERPLEXITY_API_KEY=your_api_key_here

# Required for WordPress publishing (optional)
WORDPRESS_URL=https://your-site.com
WORDPRESS_USERNAME=admin
WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### Step 5: Run the Application

```bash
python app.py
```

Open your browser to: **http://localhost:5000**

That's it! 🎉 The app will auto-seed with demo data on first run.

---

## 📖 Usage Guide

### Manual Pipeline

1. **Scrape** — Click "Scrape Now" to fetch latest news articles
2. **Generate** — Click "Generate" to create AI blog posts from articles
3. **Publish** — Click "Publish" to send drafts to WordPress
4. Or use **"Run Full Pipeline"** to do all three in sequence

### Automated Mode

1. Click **"Start Auto"** in the top bar
2. The pipeline runs automatically every 60 minutes (configurable)
3. New articles → Blog posts → WordPress drafts (if configured)

### WordPress Setup

1. In WordPress Admin, go to **Users → Profile**
2. Scroll to **Application Passwords**
3. Create a new application password named "WasteWatch AI"
4. Copy the password to your `.env` file

### Custom Blog Prompt

Edit the `BLOG_PROMPT_TEMPLATE` in `config.py` to customize how blog posts are generated. The template supports these variables:
- `{title}` — Article headline
- `{source}` — News source name
- `{date}` — Publication date
- `{summary}` — Article summary
- `{content}` — Full article content

---

## 🏗️ Project Structure

```
wastewatch-ai/
├── app.py                  # Main Flask application & routes
├── config.py               # Configuration & settings
├── models.py               # Database models (Peewee ORM)
├── scraper.py              # News scraping engine
├── blog_generator.py       # AI blog post generation
├── wordpress_publisher.py  # WordPress REST API integration
├── scheduler.py            # Background task scheduler
├── requirements.txt        # Python dependencies
├── .env.example            # Configuration template
├── templates/              # HTML templates
│   ├── base.html           # Layout template
│   ├── dashboard.html      # Main dashboard page
│   ├── articles.html       # Articles listing
│   ├── blogs.html          # Blog posts listing
│   ├── blog_detail.html    # Single blog post view
│   └── blog_preview.html   # Blog post preview
├── static/                 # Static assets
│   ├── styles.css          # Design system CSS
│   └── app.js              # Frontend JavaScript
└── generated_posts/        # Exported HTML blog posts
```

---

## 🔧 Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `PERPLEXITY_API_KEY` | — | Your Perplexity Pro API key |
| `WORDPRESS_URL` | — | WordPress site URL |
| `WORDPRESS_USERNAME` | — | WordPress username |
| `WORDPRESS_APP_PASSWORD` | — | WordPress application password |
| `SCRAPE_INTERVAL_MINUTES` | `60` | Auto-scrape interval in minutes |
| `MAX_ARTICLES_PER_RUN` | `10` | Max articles to scrape per feed |
| `AUTO_GENERATE_BLOGS` | `true` | Auto-generate blogs after scraping |
| `AUTO_PUBLISH_DRAFTS` | `false` | Auto-publish to WordPress |
| `FLASK_PORT` | `5000` | Web dashboard port |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/scrape` | Trigger manual scrape |
| `POST` | `/api/generate` | Generate blog posts (all pending) |
| `POST` | `/api/generate/<article_id>` | Generate from specific article |
| `POST` | `/api/publish/<blog_id>` | Publish to WordPress |
| `POST` | `/api/export/<blog_id>` | Export as HTML file |
| `POST` | `/api/wordpress/test` | Test WordPress connection |
| `POST` | `/api/scheduler/start` | Start auto-scheduler |
| `POST` | `/api/scheduler/stop` | Stop auto-scheduler |
| `GET`  | `/api/scheduler/status` | Get scheduler status |
| `GET`  | `/api/stats` | Get dashboard statistics |

---

## 📰 News Sources

The scraper monitors these RSS feeds by default:

- **Google News** — Multiple search queries for wastewater/pollution topics
- **EPA News Releases** — Official EPA announcements
- **Water Online** — Industry publication
- **WaterWorld** — Water/wastewater industry news

You can add custom RSS feeds in `config.py` → `RSS_FEEDS` list.

---

## 🧪 Demo Mode

The app works fully in demo mode without any API keys:
- **Demo articles** are auto-seeded on first run
- **Blog posts** are generated using realistic templates
- **WordPress publishing** is simulated

This makes it perfect for portfolio demonstrations!

---

## 📋 Tech Stack

- **Backend:** Python 3.9+, Flask
- **Database:** SQLite (via Peewee ORM)
- **Scraping:** feedparser, BeautifulSoup4, requests
- **AI:** Perplexity Pro API (OpenAI-compatible)
- **CMS:** WordPress REST API
- **Scheduling:** APScheduler
- **Frontend:** Vanilla HTML/CSS/JS, Lucide Icons

---

## 📄 License

MIT License — feel free to use this project for your portfolio or commercial purposes.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

<p align="center">
  Built with ❤️ by WasteWatch AI Team
</p>
