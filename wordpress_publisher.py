"""
WasteWatch AI - WordPress Publisher Module
Publishes blog posts to WordPress via REST API.
"""

import re
import os
import json
import logging
import base64
from datetime import datetime

import requests

from config import Config
from models import BlogPost

logger = logging.getLogger("wastewatch.wordpress")


class WordPressPublisher:
    """Handles publishing blog posts to WordPress via REST API."""

    def __init__(self):
        self.site_url = Config.WORDPRESS_URL.rstrip("/")
        self.username = Config.WORDPRESS_USERNAME
        self.app_password = Config.WORDPRESS_APP_PASSWORD
        self.api_url = f"{self.site_url}/wp-json/wp/v2"

    def is_configured(self):
        """Check if WordPress credentials are configured."""
        return bool(
            self.site_url
            and self.username
            and self.app_password
            and self.site_url != "https://your-wordpress-site.com"
        )

    def _get_auth_headers(self):
        """Get authentication headers for WordPress API."""
        credentials = f"{self.username}:{self.app_password}"
        token = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "User-Agent": "WasteWatch-AI/1.0",
        }

    def test_connection(self):
        """Test the WordPress API connection."""
        if not self.is_configured():
            return {
                "success": False,
                "message": "WordPress is not configured. Add credentials to .env file.",
            }

        try:
            response = requests.get(
                f"{self.api_url}/users/me",
                headers=self._get_auth_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                user_data = response.json()
                return {
                    "success": True,
                    "message": f"Connected as: {user_data.get('name', 'Unknown')}",
                    "user": user_data.get("name"),
                }
            else:
                return {
                    "success": False,
                    "message": f"Authentication failed (HTTP {response.status_code})",
                }

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "message": f"Cannot connect to {self.site_url}. Check the URL.",
            }
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}

    def upload_image(self, image_path):
        """Upload an image to WordPress media library."""
        if not os.path.exists(image_path):
            logger.warning(f"Image not found: {image_path}")
            return None

        try:
            filename = os.path.basename(image_path)
            with open(image_path, "rb") as img_file:
                headers = self._get_auth_headers()
                headers["Content-Type"] = "image/jpeg"
                headers["Content-Disposition"] = f'attachment; filename="{filename}"'

                response = requests.post(
                    f"{self.api_url}/media",
                    headers=headers,
                    data=img_file.read(),
                    timeout=30,
                )

                if response.status_code == 201:
                    media_data = response.json()
                    logger.info(f"📸 Image uploaded: {media_data.get('source_url')}")
                    return {
                        "id": media_data["id"],
                        "url": media_data.get("source_url", ""),
                    }
                else:
                    logger.error(f"Image upload failed: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Image upload error: {e}")
            return None

    def create_or_get_tags(self, tag_names):
        """Create tags in WordPress and return their IDs."""
        tag_ids = []

        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if not tag_name:
                continue

            try:
                # Check if tag exists
                response = requests.get(
                    f"{self.api_url}/tags",
                    params={"search": tag_name},
                    headers=self._get_auth_headers(),
                    timeout=10,
                )

                if response.status_code == 200:
                    tags = response.json()
                    if tags:
                        tag_ids.append(tags[0]["id"])
                        continue

                # Create new tag
                response = requests.post(
                    f"{self.api_url}/tags",
                    headers=self._get_auth_headers(),
                    json={"name": tag_name},
                    timeout=10,
                )

                if response.status_code == 201:
                    tag_ids.append(response.json()["id"])

            except Exception as e:
                logger.warning(f"Tag creation error for '{tag_name}': {e}")

        return tag_ids

    def publish_post(self, blog_post, status="draft", featured_image_id=None):
        """Publish a blog post to WordPress."""
        if not self.is_configured():
            return {
                "success": False,
                "message": "WordPress not configured",
            }

        try:
            # Prepare post data
            post_data = {
                "title": blog_post.headline,
                "content": blog_post.content,
                "status": status,  # 'draft', 'publish', 'pending'
                "excerpt": blog_post.meta_description,
                "format": "standard",
            }

            # Add tags
            if blog_post.tags:
                tag_names = [t.strip() for t in blog_post.tags.split(",")]
                tag_ids = self.create_or_get_tags(tag_names)
                if tag_ids:
                    post_data["tags"] = tag_ids

            # Add featured image
            if featured_image_id:
                post_data["featured_media"] = featured_image_id

            # Create the post
            response = requests.post(
                f"{self.api_url}/posts",
                headers=self._get_auth_headers(),
                json=post_data,
                timeout=30,
            )

            if response.status_code == 201:
                wp_post = response.json()
                wp_post_id = wp_post["id"]
                wp_url = wp_post.get("link", "")

                # Update the database
                blog_post.wordpress_post_id = wp_post_id
                blog_post.wordpress_url = wp_url
                blog_post.status = "published" if status == "publish" else "ready"
                blog_post.published_at = datetime.utcnow()
                blog_post.save()

                logger.info(f"🚀 Published to WordPress: {wp_url}")
                return {
                    "success": True,
                    "post_id": wp_post_id,
                    "url": wp_url,
                    "message": f"Post {'published' if status == 'publish' else 'saved as draft'}!",
                }
            else:
                error_msg = response.json().get("message", "Unknown error")
                logger.error(f"WordPress publish failed: {error_msg}")
                return {
                    "success": False,
                    "message": f"Publish failed: {error_msg}",
                }

        except Exception as e:
            logger.error(f"WordPress publish error: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

    def publish_as_draft(self, blog_post, featured_image_id=None):
        """Convenience method to publish as a draft."""
        return self.publish_post(blog_post, status="draft", featured_image_id=featured_image_id)


# Singleton instance
wp_publisher = WordPressPublisher()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = wp_publisher.test_connection()
    print(f"WordPress Connection: {result}")
