"""
WasteWatch AI - Blog Generator Module
Uses Perplexity Pro API to generate professional blog posts from scraped articles.
"""

import re
import os
import json
import logging
from datetime import datetime

from openai import OpenAI

from config import Config
from models import ScrapedArticle, BlogPost, db

logger = logging.getLogger("wastewatch.blog_generator")


def get_perplexity_client():
    """Create a Perplexity API client (uses OpenAI-compatible API)."""
    api_key = Config.PERPLEXITY_API_KEY
    if not api_key or api_key == "your_perplexity_api_key_here":
        return None

    return OpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai",
    )


def generate_blog_post(article, custom_prompt=None):
    """Generate a blog post from a scraped article using Perplexity Pro."""
    client = get_perplexity_client()

    # Build the prompt: parameter > saved DB setting > Config default
    if custom_prompt:
        prompt_template = custom_prompt
    else:
        try:
            from models import AppSettings
            saved_prompt = AppSettings.get_value("BLOG_PROMPT_TEMPLATE", "")
            prompt_template = saved_prompt if saved_prompt else Config.BLOG_PROMPT_TEMPLATE
        except Exception:
            prompt_template = Config.BLOG_PROMPT_TEMPLATE

    prompt = prompt_template.format(
        title=article.title,
        source=article.source,
        date=article.published_date or "Unknown",
        summary=article.summary,
        content=article.content or article.summary,
    )

    if client:
        # Use actual Perplexity API
        try:
            response = client.chat.completions.create(
                model="sonar-pro",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional environmental journalist specializing in wastewater treatment and water pollution. Write engaging, well-researched blog posts.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4000,
                temperature=0.7,
            )

            generated_text = response.choices[0].message.content
            return parse_blog_response(generated_text, article)

        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return generate_demo_blog(article)
    else:
        # Demo mode - generate a realistic blog post without API
        logger.info("⚡ Running in demo mode (no API key configured)")
        return generate_demo_blog(article)


def parse_blog_response(text, article):
    """Parse the AI-generated response into structured blog data."""
    result = {
        "headline": "",
        "meta_description": "",
        "tags": "",
        "featured_image_prompt": "",
        "content": "",
    }

    # Extract headline
    headline_match = re.search(r"## HEADLINE:\s*(.+?)(?:\n|$)", text)
    if headline_match:
        result["headline"] = headline_match.group(1).strip()
    else:
        result["headline"] = f"Analysis: {article.title}"

    # Extract meta description
    meta_match = re.search(r"## META_DESCRIPTION:\s*(.+?)(?:\n|$)", text)
    if meta_match:
        result["meta_description"] = meta_match.group(1).strip()

    # Extract tags
    tags_match = re.search(r"## TAGS:\s*(.+?)(?:\n|$)", text)
    if tags_match:
        result["tags"] = tags_match.group(1).strip()

    # Extract image prompt
    img_match = re.search(r"## FEATURED_IMAGE_PROMPT:\s*(.+?)(?:\n|$)", text)
    if img_match:
        result["featured_image_prompt"] = img_match.group(1).strip()

    # Extract content (everything after ## CONTENT:)
    content_match = re.search(r"## CONTENT:\s*\n(.*)", text, re.DOTALL)
    if content_match:
        result["content"] = content_match.group(1).strip()
    else:
        # If parsing fails, use the full text
        result["content"] = text

    return result


def generate_demo_blog(article):
    """Generate a realistic demo blog post without API access."""

    headline = _generate_headline(article.title)
    tags = _generate_tags(article.title, article.summary)

    content = f"""<p class="lead"><strong>{headline}</strong> — In a development that underscores the ongoing challenges facing water treatment infrastructure, {article.summary[:200]}...</p>

<h2>What Happened</h2>
<p>{article.content[:800] if article.content else article.summary}</p>

<h2>Environmental Impact Assessment</h2>
<p>The incident raises serious concerns about the effectiveness of current wastewater treatment protocols and their ability to protect public health and aquatic ecosystems. Environmental scientists have noted that events like these can have cascading effects on local water systems, affecting everything from drinking water supplies to recreational waterways.</p>

<p>According to the Environmental Protection Agency, wastewater treatment violations have increased by approximately 12% over the past five years, highlighting a growing infrastructure crisis that demands immediate attention from policymakers and industry stakeholders.</p>

<h2>Regulatory Context</h2>
<p>This incident occurs against a backdrop of increasing scrutiny of wastewater treatment practices nationwide. The Clean Water Act, which forms the backbone of water pollution regulation in the United States, requires facilities to meet specific effluent standards. However, aging infrastructure and increasing demand have made compliance increasingly challenging for many treatment plants.</p>

<blockquote>
<p>"The wastewater treatment industry is at a crossroads. We must invest in modernizing our infrastructure or face increasingly severe environmental consequences." — American Water Works Association</p>
</blockquote>

<h2>Industry Implications</h2>
<p>For wastewater treatment professionals, this incident serves as a stark reminder of the importance of maintaining robust monitoring systems, investing in treatment technology upgrades, and ensuring regulatory compliance. The industry is increasingly looking toward advanced treatment technologies, including membrane bioreactors, UV disinfection, and AI-powered monitoring systems, to address these challenges.</p>

<h2>What This Means Going Forward</h2>
<p>As communities continue to grapple with aging water infrastructure and increasing environmental regulations, incidents like this highlight the urgent need for:</p>
<ul>
<li><strong>Infrastructure Investment:</strong> Upgrading aging treatment plants to meet modern standards</li>
<li><strong>Enhanced Monitoring:</strong> Implementing real-time water quality monitoring systems</li>
<li><strong>Regulatory Reform:</strong> Strengthening enforcement mechanisms and increasing penalties for violations</li>
<li><strong>Public Awareness:</strong> Educating communities about the importance of water treatment infrastructure</li>
<li><strong>Innovation:</strong> Investing in new treatment technologies to address emerging contaminants</li>
</ul>

<p>The wastewater treatment industry must rise to meet these challenges head-on. The health of our waterways — and the communities that depend on them — hangs in the balance.</p>

<p><em>Stay informed about the latest developments in wastewater treatment and water quality by subscribing to our newsletter.</em></p>"""

    meta_description = f"Analysis of {article.title[:80]}. Expert insights on wastewater treatment impacts and environmental implications."

    image_prompt = f"Dramatic environmental photography of water treatment facility with industrial pipes and water flow, blue and green tones, editorial style"

    return {
        "headline": headline,
        "meta_description": meta_description[:160],
        "tags": tags,
        "featured_image_prompt": image_prompt,
        "content": content,
    }


def _generate_headline(original_title):
    """Generate an alternative headline."""
    patterns = [
        "Breaking: {topic} — What It Means for Water Quality",
        "Inside the Crisis: {topic}",
        "Water Watch: {topic} Raises Industry Alarm",
        "Environmental Alert: {topic}",
        "Analysis: The Growing Threat Behind {topic}",
    ]

    # Simplify the title for the template
    topic = original_title
    if len(topic) > 60:
        topic = topic[:57] + "..."

    import random
    pattern = random.choice(patterns)
    return pattern.format(topic=topic)


def _generate_tags(title, summary):
    """Generate relevant tags based on content."""
    all_tags = []
    text = f"{title} {summary}".lower()

    tag_map = {
        "wastewater treatment": ["wastewater treatment", "water treatment"],
        "sewage": ["sewage", "sewage treatment"],
        "pollution": ["water pollution", "environmental pollution"],
        "epa": ["EPA", "environmental regulation"],
        "clean water act": ["Clean Water Act", "federal regulation"],
        "spill": ["pollution incident", "environmental emergency"],
        "contamination": ["water contamination", "public health"],
        "pfas": ["PFAS", "forever chemicals"],
        "algal bloom": ["harmful algal blooms", "HABs"],
        "red tide": ["red tide", "algal blooms"],
        "fine": ["environmental enforcement", "EPA fines"],
        "discharge": ["industrial discharge", "effluent"],
        "infrastructure": ["water infrastructure", "infrastructure investment"],
    }

    for keyword, tags in tag_map.items():
        if keyword in text:
            all_tags.extend(tags)

    # Remove duplicates and limit
    seen = set()
    unique_tags = []
    for tag in all_tags:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            unique_tags.append(tag)

    return ", ".join(unique_tags[:6])


def process_article(article, custom_prompt=None):
    """Process a single article: generate blog post and save to database."""
    logger.info(f"📝 Generating blog post for: {article.title[:60]}...")

    try:
        blog_data = generate_blog_post(article, custom_prompt)

        # Save to database
        blog_post = BlogPost.create(
            article_id=article.id,
            headline=blog_data["headline"],
            meta_description=blog_data.get("meta_description", ""),
            content=blog_data["content"],
            tags=blog_data.get("tags", ""),
            featured_image_prompt=blog_data.get("featured_image_prompt", ""),
            status="draft",
        )

        # Mark article as processed
        article.blog_generated = True
        article.save()

        logger.info(f"✅ Blog post created: {blog_data['headline'][:60]}...")
        return blog_post

    except Exception as e:
        logger.error(f"❌ Failed to generate blog: {e}")
        return None


def process_all_unprocessed(custom_prompt=None, limit=5):
    """Process all unprocessed articles."""
    from scraper import get_unprocessed_articles

    articles = get_unprocessed_articles(limit=limit)
    results = []

    for article in articles:
        blog = process_article(article, custom_prompt)
        if blog:
            results.append(blog)

    return results


def export_blog_to_html(blog_post, output_dir="generated_posts"):
    """Export a blog post as a standalone HTML file for easy WordPress upload."""
    os.makedirs(output_dir, exist_ok=True)

    # Create a clean filename
    slug = re.sub(r"[^a-z0-9]+", "-", blog_post.headline.lower()).strip("-")[:50]
    filename = f"{slug}.html"
    filepath = os.path.join(output_dir, filename)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="description" content="{blog_post.meta_description}">
    <title>{blog_post.headline}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.8; color: #333; }}
        h1 {{ color: #1a5276; font-size: 2em; }}
        h2 {{ color: #2471a3; margin-top: 30px; }}
        h3 {{ color: #2e86c1; }}
        blockquote {{ border-left: 4px solid #2471a3; padding: 10px 20px; margin: 20px 0; background: #eaf2f8; font-style: italic; }}
        .lead {{ font-size: 1.1em; color: #555; }}
        .meta {{ color: #888; font-size: 0.9em; margin-bottom: 20px; }}
        .tags {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
        .tag {{ display: inline-block; background: #2471a3; color: white; padding: 4px 12px; border-radius: 15px; margin: 2px; font-size: 0.85em; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; }}
    </style>
</head>
<body>
    <article>
        <h1>{blog_post.headline}</h1>
        <div class="meta">
            Published: {blog_post.created_at.strftime('%B %d, %Y')} | WasteWatch AI
        </div>
        {blog_post.content}
        <div class="tags">
            <strong>Tags:</strong>
            {''.join(f'<span class="tag">{tag.strip()}</span>' for tag in blog_post.tags.split(",") if tag.strip())}
        </div>
    </article>
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"📄 Exported: {filepath}")
    return filepath


if __name__ == "__main__":
    from models import init_db
    init_db()

    logging.basicConfig(level=logging.INFO)
    results = process_all_unprocessed()
    print(f"\nGenerated {len(results)} blog posts")

    for blog in results:
        path = export_blog_to_html(blog)
        print(f"  Exported: {path}")
