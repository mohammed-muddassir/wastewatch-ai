"""
WasteWatch AI - Background Scheduler
Runs scraping and blog generation on a configurable schedule.
"""

import logging
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import Config

logger = logging.getLogger("wastewatch.scheduler")

scheduler = BackgroundScheduler(daemon=True)
_is_running = False


def scheduled_scrape_and_generate():
    """Run the full pipeline: scrape → generate → optionally publish."""
    global _is_running

    if _is_running:
        logger.info("⏭️ Previous run still in progress, skipping...")
        return

    _is_running = True
    logger.info(f"⏰ Scheduled run started at {datetime.utcnow()}")

    try:
        # Import here to avoid circular imports
        from models import init_db
        from scraper import run_scraper
        from blog_generator import process_all_unprocessed
        from wordpress_publisher import wp_publisher

        # Step 1: Scrape for new articles
        scrape_result = run_scraper()
        logger.info(f"  Scrape: {scrape_result['new']} new articles")

        # Step 2: Generate blog posts (if enabled)
        if Config.AUTO_GENERATE_BLOGS and scrape_result["new"] > 0:
            blogs = process_all_unprocessed(limit=scrape_result["new"])
            logger.info(f"  Generated: {len(blogs)} blog posts")

            # Step 3: Publish to WordPress (if enabled)
            if Config.AUTO_PUBLISH_DRAFTS and wp_publisher.is_configured():
                published = 0
                for blog in blogs:
                    result = wp_publisher.publish_as_draft(blog)
                    if result["success"]:
                        published += 1
                logger.info(f"  Published: {published} drafts to WordPress")

    except Exception as e:
        logger.error(f"❌ Scheduled run failed: {e}")
    finally:
        _is_running = False


def start_scheduler():
    """Start the background scheduler."""
    interval_minutes = Config.SCRAPE_INTERVAL_MINUTES

    scheduler.add_job(
        scheduled_scrape_and_generate,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="scrape_and_generate",
        name="Scrape & Generate Blog Posts",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"📅 Scheduler started! Running every {interval_minutes} minutes."
    )


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("⏹️ Scheduler stopped.")


def get_scheduler_status():
    """Get the current scheduler status."""
    jobs = scheduler.get_jobs()
    if not jobs:
        return {"running": False, "next_run": None, "interval": None}

    job = jobs[0]
    return {
        "running": scheduler.running,
        "next_run": str(job.next_run_time) if job.next_run_time else None,
        "interval": f"Every {Config.SCRAPE_INTERVAL_MINUTES} minutes",
        "is_processing": _is_running,
    }
