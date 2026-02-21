"""
WasteWatch AI - Main Application
Flask web dashboard for managing the scraping pipeline.
"""

import os
import json
import logging
from datetime import datetime

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash

from config import Config, get_setting
from models import init_db, ScrapedArticle, BlogPost, ScrapeLog, AppSettings, db
from scraper import run_scraper, seed_demo_data, get_unprocessed_articles
from blog_generator import process_article, process_all_unprocessed, export_blog_to_html
from wordpress_publisher import wp_publisher
from scheduler import start_scheduler, stop_scheduler, get_scheduler_status, scheduled_scrape_and_generate

# ===== Setup =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("wastewatch")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = Config.FLASK_SECRET_KEY


# ===== Template Filters =====
@app.template_filter("timeago")
def timeago_filter(dt):
    """Convert datetime to 'time ago' format."""
    if not dt:
        return "Unknown"
    now = datetime.utcnow()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds / 86400)
        return f"{days}d ago"


@app.template_filter("truncate_text")
def truncate_text_filter(text, length=100):
    """Truncate text to specified length."""
    if not text:
        return ""
    if len(text) <= length:
        return text
    return text[:length] + "..."


# ===== Context Processor =====
@app.context_processor
def inject_global_context():
    """Inject common variables into all templates."""
    return {
        "scheduler": get_scheduler_status(),
        "wp_configured": wp_publisher.is_configured(),
        "has_api_key": bool(
            Config.PERPLEXITY_API_KEY
            and Config.PERPLEXITY_API_KEY != "your_perplexity_api_key_here"
        ),
    }


# ===== Routes =====

@app.route("/")
def dashboard():
    """Main dashboard page."""
    # Gather stats
    total_articles = ScrapedArticle.select().count()
    total_blogs = BlogPost.select().count()
    unprocessed = ScrapedArticle.select().where(
        (ScrapedArticle.blog_generated == False) & (ScrapedArticle.is_relevant == True)
    ).count()
    published = BlogPost.select().where(BlogPost.status == "published").count()
    drafts = BlogPost.select().where(BlogPost.status == "draft").count()

    # Recent articles
    recent_articles = (
        ScrapedArticle.select()
        .order_by(ScrapedArticle.scraped_at.desc())
        .limit(5)
    )

    # Recent blog posts
    recent_blogs = (
        BlogPost.select()
        .order_by(BlogPost.created_at.desc())
        .limit(5)
    )

    # Recent scrape logs
    recent_logs = (
        ScrapeLog.select()
        .order_by(ScrapeLog.run_at.desc())
        .limit(5)
    )

    # Scheduler status
    sched_status = get_scheduler_status()

    # WordPress status
    wp_configured = wp_publisher.is_configured()

    return render_template(
        "dashboard.html",
        stats={
            "total_articles": total_articles,
            "total_blogs": total_blogs,
            "unprocessed": unprocessed,
            "published": published,
            "drafts": drafts,
        },
        recent_articles=recent_articles,
        recent_blogs=recent_blogs,
        recent_logs=recent_logs,
        scheduler=sched_status,
        wp_configured=wp_configured,
        has_api_key=bool(Config.PERPLEXITY_API_KEY and Config.PERPLEXITY_API_KEY != "your_perplexity_api_key_here"),
    )


@app.route("/articles")
def articles():
    """View all scraped articles."""
    page = int(request.args.get("page", 1))
    per_page = 20

    query = ScrapedArticle.select().order_by(ScrapedArticle.scraped_at.desc())
    total = query.count()
    articles_list = query.paginate(page, per_page)

    return render_template(
        "articles.html",
        articles=articles_list,
        page=page,
        total=total,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page,
    )


@app.route("/blogs")
def blogs():
    """View all generated blog posts."""
    page = int(request.args.get("page", 1))
    per_page = 20

    query = BlogPost.select().order_by(BlogPost.created_at.desc())
    total = query.count()
    blogs_list = query.paginate(page, per_page)

    return render_template(
        "blogs.html",
        blogs=blogs_list,
        page=page,
        total=total,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page,
    )


@app.route("/blog/<int:blog_id>")
def view_blog(blog_id):
    """View a single blog post."""
    blog = BlogPost.get_or_none(BlogPost.id == blog_id)
    if not blog:
        flash("Blog post not found.", "error")
        return redirect(url_for("blogs"))

    # Get the source article
    article = None
    if blog.article_id:
        article = ScrapedArticle.get_or_none(ScrapedArticle.id == blog.article_id)

    return render_template("blog_detail.html", blog=blog, article=article)


@app.route("/blog/<int:blog_id>/preview")
def preview_blog(blog_id):
    """Preview a blog post as it would appear on WordPress."""
    blog = BlogPost.get_or_none(BlogPost.id == blog_id)
    if not blog:
        return "Blog post not found", 404

    return render_template("blog_preview.html", blog=blog)


@app.route("/settings")
def settings_page():
    """Settings page for API keys and configuration."""
    # Load all saved settings from DB
    saved = {}
    setting_keys = [
        "PERPLEXITY_API_KEY", "WORDPRESS_URL", "WORDPRESS_USERNAME",
        "WORDPRESS_APP_PASSWORD", "SCRAPE_INTERVAL_MINUTES",
        "MAX_ARTICLES_PER_RUN", "AUTO_GENERATE_BLOGS",
        "AUTO_PUBLISH_DRAFTS", "BLOG_PROMPT_TEMPLATE",
    ]
    for key in setting_keys:
        val = get_setting(key, "")
        if val:
            saved[key] = val

    return render_template(
        "settings.html",
        settings=saved,
        default_prompt=Config.BLOG_PROMPT_TEMPLATE,
    )


# ===== API Routes =====

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """Trigger a manual scrape."""
    try:
        result = run_scraper()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """Generate blog posts from unprocessed articles."""
    try:
        limit = int(request.json.get("limit", 5)) if request.json else 5
        custom_prompt = request.json.get("prompt") if request.json else None
        blogs = process_all_unprocessed(custom_prompt=custom_prompt, limit=limit)
        return jsonify({
            "success": True,
            "generated": len(blogs),
            "posts": [{"id": b.id, "headline": b.headline} for b in blogs],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate/<int:article_id>", methods=["POST"])
def api_generate_single(article_id):
    """Generate a blog post from a specific article."""
    try:
        article = ScrapedArticle.get_or_none(ScrapedArticle.id == article_id)
        if not article:
            return jsonify({"success": False, "error": "Article not found"}), 404

        custom_prompt = request.json.get("prompt") if request.json else None
        blog = process_article(article, custom_prompt)

        if blog:
            return jsonify({
                "success": True,
                "post": {"id": blog.id, "headline": blog.headline},
            })
        else:
            return jsonify({"success": False, "error": "Generation failed"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/publish/<int:blog_id>", methods=["POST"])
def api_publish(blog_id):
    """Publish a blog post to WordPress as a draft."""
    try:
        blog = BlogPost.get_or_none(BlogPost.id == blog_id)
        if not blog:
            return jsonify({"success": False, "error": "Blog post not found"}), 404

        if not wp_publisher.is_configured():
            return jsonify({
                "success": False,
                "error": "WordPress is not configured. Add credentials to .env file.",
            }), 400

        result = wp_publisher.publish_as_draft(blog)
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/export/<int:blog_id>", methods=["POST"])
def api_export(blog_id):
    """Export a blog post as HTML file."""
    try:
        blog = BlogPost.get_or_none(BlogPost.id == blog_id)
        if not blog:
            return jsonify({"success": False, "error": "Blog post not found"}), 404

        filepath = export_blog_to_html(blog)
        return jsonify({"success": True, "filepath": filepath})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/wordpress/test", methods=["POST"])
def api_test_wordpress():
    """Test WordPress connection."""
    result = wp_publisher.test_connection()
    return jsonify(result)


@app.route("/api/scheduler/start", methods=["POST"])
def api_start_scheduler():
    """Start the background scheduler."""
    try:
        start_scheduler()
        return jsonify({"success": True, "message": "Scheduler started!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scheduler/stop", methods=["POST"])
def api_stop_scheduler():
    """Stop the background scheduler."""
    try:
        stop_scheduler()
        return jsonify({"success": True, "message": "Scheduler stopped."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scheduler/status", methods=["GET"])
def api_scheduler_status():
    """Get scheduler status."""
    return jsonify(get_scheduler_status())


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Get dashboard statistics."""
    return jsonify({
        "total_articles": ScrapedArticle.select().count(),
        "total_blogs": BlogPost.select().count(),
        "unprocessed": ScrapedArticle.select().where(
            (ScrapedArticle.blog_generated == False) & (ScrapedArticle.is_relevant == True)
        ).count(),
        "published": BlogPost.select().where(BlogPost.status == "published").count(),
        "drafts": BlogPost.select().where(BlogPost.status == "draft").count(),
    })


@app.route("/api/seed-demo", methods=["POST"])
def api_seed_demo():
    """Seed the database with demo data."""
    try:
        count = seed_demo_data()
        return jsonify({"success": True, "seeded": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    """Save settings to the database."""
    try:
        data = request.json or {}
        saved_keys = []

        for key, value in data.items():
            AppSettings.set_value(key, value)
            saved_keys.append(key)

        # Refresh Config values that are used at runtime
        if "PERPLEXITY_API_KEY" in data:
            Config.PERPLEXITY_API_KEY = data["PERPLEXITY_API_KEY"]
        if "WORDPRESS_URL" in data:
            Config.WORDPRESS_URL = data["WORDPRESS_URL"]
        if "WORDPRESS_USERNAME" in data:
            Config.WORDPRESS_USERNAME = data["WORDPRESS_USERNAME"]
        if "WORDPRESS_APP_PASSWORD" in data:
            Config.WORDPRESS_APP_PASSWORD = data["WORDPRESS_APP_PASSWORD"]
        if "SCRAPE_INTERVAL_MINUTES" in data:
            try:
                Config.SCRAPE_INTERVAL_MINUTES = int(data["SCRAPE_INTERVAL_MINUTES"])
            except ValueError:
                pass
        if "MAX_ARTICLES_PER_RUN" in data:
            try:
                Config.MAX_ARTICLES_PER_RUN = int(data["MAX_ARTICLES_PER_RUN"])
            except ValueError:
                pass

        return jsonify({"success": True, "saved": saved_keys})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/article/<int:article_id>/delete", methods=["DELETE"])
def api_delete_article(article_id):
    """Delete an article."""
    try:
        article = ScrapedArticle.get_or_none(ScrapedArticle.id == article_id)
        if article:
            article.delete_instance()
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/blog/<int:blog_id>/delete", methods=["DELETE"])
def api_delete_blog(blog_id):
    """Delete a blog post."""
    try:
        blog = BlogPost.get_or_none(BlogPost.id == blog_id)
        if blog:
            blog.delete_instance()
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===== App Initialization =====
# Called at module level so both gunicorn (app:app) and direct run (python app.py) work

def create_app():
    """Initialize the application."""
    init_db()

    # Seed demo data if database is empty
    if ScrapedArticle.select().count() == 0:
        logger.info("🌱 Empty database detected, seeding demo data...")
        seed_demo_data()

        # Auto-generate blog posts for demo articles
        logger.info("📝 Generating demo blog posts...")
        process_all_unprocessed(limit=5)

    return app


# Initialize on import (gunicorn needs this)
app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", Config.FLASK_PORT))
    logger.info(f"🚀 WasteWatch AI starting on http://localhost:{port}")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=Config.FLASK_DEBUG,
    )

