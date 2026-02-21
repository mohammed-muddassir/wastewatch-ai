"""
WasteWatch AI - Database Models
SQLite database models using Peewee ORM.
"""

import os
from datetime import datetime
from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    TextField,
    DateTimeField,
    BooleanField,
    IntegerField,
    AutoField,
)

# Database file in project root
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wastewatch.db")
db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    """Base model with database binding."""
    class Meta:
        database = db


class ScrapedArticle(BaseModel):
    """Stores scraped news articles."""
    id = AutoField()
    title = CharField(max_length=500)
    url = CharField(max_length=1000, unique=True)
    source = CharField(max_length=200, default="Unknown")
    summary = TextField(default="")
    content = TextField(default="")
    published_date = DateTimeField(null=True)
    scraped_at = DateTimeField(default=datetime.utcnow)
    is_relevant = BooleanField(default=True)
    blog_generated = BooleanField(default=False)

    class Meta:
        table_name = "scraped_articles"

    def __str__(self):
        return f"[{self.source}] {self.title}"


class BlogPost(BaseModel):
    """Stores generated blog posts."""
    id = AutoField()
    article_id = IntegerField(null=True)
    headline = CharField(max_length=500)
    meta_description = CharField(max_length=300, default="")
    content = TextField()
    tags = CharField(max_length=500, default="")
    featured_image_prompt = CharField(max_length=500, default="")
    featured_image_url = CharField(max_length=1000, default="")
    status = CharField(
        max_length=50, default="draft"
    )  # draft, ready, published, failed
    wordpress_post_id = IntegerField(null=True)
    wordpress_url = CharField(max_length=1000, default="")
    created_at = DateTimeField(default=datetime.utcnow)
    published_at = DateTimeField(null=True)

    class Meta:
        table_name = "blog_posts"

    def __str__(self):
        return f"[{self.status}] {self.headline}"


class ScrapeLog(BaseModel):
    """Logs scraping activity."""
    id = AutoField()
    run_at = DateTimeField(default=datetime.utcnow)
    articles_found = IntegerField(default=0)
    articles_new = IntegerField(default=0)
    blogs_generated = IntegerField(default=0)
    blogs_published = IntegerField(default=0)
    errors = TextField(default="")
    status = CharField(max_length=50, default="success")  # success, partial, failed

    class Meta:
        table_name = "scrape_logs"


class AppSettings(BaseModel):
    """Key-value store for application settings (API keys, preferences)."""
    key = CharField(max_length=200, unique=True)
    value = TextField(default="")
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "app_settings"

    @classmethod
    def get_value(cls, key, default=""):
        """Get a setting value by key."""
        try:
            setting = cls.get_or_none(cls.key == key)
            return setting.value if setting else default
        except Exception:
            return default

    @classmethod
    def set_value(cls, key, value):
        """Set a setting value (create or update)."""
        setting, created = cls.get_or_create(
            key=key, defaults={"value": value, "updated_at": datetime.utcnow()}
        )
        if not created:
            setting.value = value
            setting.updated_at = datetime.utcnow()
            setting.save()
        return setting


def init_db():
    """Initialize the database and create tables."""
    db.connect(reuse_if_open=True)
    db.create_tables([ScrapedArticle, BlogPost, ScrapeLog, AppSettings], safe=True)
    print(f"✅ Database initialized at: {DB_PATH}")


if __name__ == "__main__":
    init_db()
    print("Database tables created successfully!")
