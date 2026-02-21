"""
WasteWatch AI - Configuration Manager
Loads settings from .env file and provides defaults.
Checks database (AppSettings) first, then .env, then hardcoded defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def get_setting(key, default=""):
    """Get a setting: check AppSettings DB first, then .env, then default."""
    try:
        from models import AppSettings
        db_val = AppSettings.get_value(key, None)
        if db_val is not None and db_val != "":
            return db_val
    except Exception:
        pass  # DB not ready yet (e.g. during init)
    return os.getenv(key, default)


class Config:
    """Application configuration."""

    # --- Perplexity API ---
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

    # --- WordPress ---
    WORDPRESS_URL = os.getenv("WORDPRESS_URL", "")
    WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME", "")
    WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD", "")

    # --- Scraping ---
    SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "60"))
    MAX_ARTICLES_PER_RUN = int(os.getenv("MAX_ARTICLES_PER_RUN", "10"))

    # --- Blog Generation ---
    AUTO_GENERATE_BLOGS = os.getenv("AUTO_GENERATE_BLOGS", "true").lower() == "true"
    AUTO_PUBLISH_DRAFTS = os.getenv("AUTO_PUBLISH_DRAFTS", "false").lower() == "true"

    # --- Flask ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # --- Source Type Toggles ---
    ENABLE_RSS_FEEDS = True
    ENABLE_GOOGLE_NEWS = True
    ENABLE_BING_NEWS = True

    # --- RSS Feed Sources ---
    RSS_FEEDS = [
        # Google News RSS searches
        "https://news.google.com/rss/search?q=wastewater+treatment+pollution&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=sewage+spill+contamination&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=water+pollution+incident&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=wastewater+discharge+violation&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=sewage+overflow+environmental&hl=en-US&gl=US&ceid=US:en",
        # EPA News
        "https://www.epa.gov/rss/epa-news-releases.xml",
        # Water Online
        "https://www.wateronline.com/rss",
        # WaterWorld
        "https://www.waterworld.com/rss",
    ]

    # --- Web Scraping Search Queries ---
    NEWS_SEARCH_QUERIES = [
        "wastewater treatment pollution incident",
        "sewage spill contamination",
        "water pollution environmental violation",
        "wastewater discharge EPA fine",
        "sewage overflow water quality",
    ]

    # --- Search Keywords ---
    KEYWORDS = [
        "wastewater treatment",
        "sewage spill",
        "water pollution",
        "effluent discharge",
        "water contamination",
        "sewage overflow",
        "wastewater violation",
        "pollution incident",
        "environmental violation water",
        "clean water act violation",
        "sewage treatment failure",
        "industrial discharge",
        "water quality violation",
    ]

    # --- Blog Prompt Template ---
    BLOG_PROMPT_TEMPLATE = """You are a professional environmental journalist and blogger specializing in wastewater treatment and water pollution issues. 

Based on the following news article(s), write a comprehensive, engaging blog post for a WordPress website focused on wastewater treatment industry news and pollution incidents.

ARTICLE INFORMATION:
Title: {title}
Source: {source}
Date: {date}
Summary: {summary}
Full Content: {content}

BLOG POST REQUIREMENTS:
1. Write an attention-grabbing headline (different from the original article title)
2. Write a compelling introduction that hooks the reader
3. Provide detailed analysis of the incident/news
4. Include relevant context about wastewater treatment regulations
5. Discuss potential environmental and public health impacts
6. Add expert-level commentary on industry implications
7. Include a conclusion with forward-looking perspective
8. Suggest 3-5 relevant tags for SEO
9. Write a meta description (150-160 characters) for SEO

FORMAT YOUR RESPONSE AS:
## HEADLINE: [Your headline]
## META_DESCRIPTION: [SEO meta description]
## TAGS: [comma-separated tags]
## FEATURED_IMAGE_PROMPT: [A description for generating a relevant featured image]
## CONTENT:
[Full blog post content in HTML format, using <h2>, <h3>, <p>, <ul>, <li>, <blockquote> tags]
"""

    @classmethod
    def get_live(cls, key):
        """Get a live setting value (checks DB first, then class attr, then .env)."""
        return get_setting(key, getattr(cls, key, os.getenv(key, "")))

