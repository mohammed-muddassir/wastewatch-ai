"""
WasteWatch AI - News Scraper Module
Scrapes RSS feeds and news sources for wastewater treatment articles.
"""

import re
import time
import hashlib
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from config import Config
from models import ScrapedArticle, ScrapeLog, db

logger = logging.getLogger("wastewatch.scraper")

# Request headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def is_relevant(title, summary=""):
    """Check if an article is relevant to wastewater/pollution topics."""
    text = f"{title} {summary}".lower()
    relevance_score = 0

    primary_keywords = [
        "wastewater", "sewage", "water pollution", "effluent",
        "water contamination", "sewage overflow", "clean water act",
    ]
    secondary_keywords = [
        "treatment plant", "discharge", "violation", "pollution",
        "spill", "contamination", "environmental", "epa", "water quality",
    ]

    for kw in primary_keywords:
        if kw in text:
            relevance_score += 3

    for kw in secondary_keywords:
        if kw in text:
            relevance_score += 1

    return relevance_score >= 3


def extract_article_content(url):
    """Fetch and extract the main content from an article URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Remove unwanted elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "iframe", "form", "noscript"]):
            tag.decompose()

        # Try to find the main article content
        article = (
            soup.find("article")
            or soup.find("div", class_=re.compile(r"article|content|post|entry|story", re.I))
            or soup.find("main")
        )

        if article:
            paragraphs = article.find_all("p")
        else:
            paragraphs = soup.find_all("p")

        # Extract text from paragraphs
        content_parts = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 30:  # Skip very short paragraphs (ads, captions, etc.)
                content_parts.append(text)

        content = "\n\n".join(content_parts)

        # Limit content length
        if len(content) > 5000:
            content = content[:5000] + "..."

        return content if len(content) > 100 else ""

    except Exception as e:
        logger.warning(f"Failed to extract content from {url}: {e}")
        return ""


def parse_feed(feed_url):
    """Parse an RSS feed and return relevant articles."""
    articles = []

    try:
        feed = feedparser.parse(feed_url)

        if feed.bozo and not feed.entries:
            logger.warning(f"Failed to parse feed: {feed_url}")
            return articles

        for entry in feed.entries[:Config.MAX_ARTICLES_PER_RUN]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()

            # Clean HTML from summary
            if summary:
                summary = BeautifulSoup(summary, "lxml").get_text(strip=True)

            # Parse published date
            pub_date = None
            date_str = entry.get("published", entry.get("updated", ""))
            if date_str:
                try:
                    pub_date = date_parser.parse(date_str)
                except (ValueError, TypeError):
                    pub_date = None

            # Check relevance
            if not title or not link:
                continue

            if not is_relevant(title, summary):
                continue

            # Skip articles older than 7 days
            if pub_date and pub_date.replace(tzinfo=None) < datetime.utcnow() - timedelta(days=7):
                continue

            source = urlparse(feed_url).netloc or "Unknown"

            articles.append({
                "title": title,
                "url": link,
                "source": source,
                "summary": summary[:1000] if summary else "",
                "published_date": pub_date,
            })

    except Exception as e:
        logger.error(f"Error parsing feed {feed_url}: {e}")

    return articles


def scrape_google_news(query):
    """Scrape Google News search results for a query (no API key needed)."""
    articles = []
    encoded_query = quote_plus(query)
    url = f"https://www.google.com/search?q={encoded_query}&tbm=nws&hl=en"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        # Google News search result containers
        for item in soup.select("div.SoaBEf, div.xuvV6b, div.dbsr"):
            link_el = item.find("a", href=True)
            title_el = item.select_one("div.MBeuO, div.n0jPhd, div.JheGif")
            snippet_el = item.select_one("div.GI74Re, div.Y3v8qd, div.s3v9rd")
            source_el = item.select_one("div.CEMjEf span, div.XTjFC, span.WF4CUc")

            if not link_el or not title_el:
                continue

            link = link_el.get("href", "")
            if link.startswith("/url?q="):
                link = link.split("/url?q=")[1].split("&")[0]

            title = title_el.get_text(strip=True)
            summary = snippet_el.get_text(strip=True) if snippet_el else ""
            source = source_el.get_text(strip=True) if source_el else "Google News"

            if not title or not link or not is_relevant(title, summary):
                continue

            articles.append({
                "title": title,
                "url": link,
                "source": source,
                "summary": summary[:1000],
                "published_date": None,
            })

        logger.info(f"  Google News: found {len(articles)} relevant articles for '{query}'")

    except Exception as e:
        logger.warning(f"Google News scrape failed for '{query}': {e}")

    return articles[:Config.MAX_ARTICLES_PER_RUN]


def scrape_bing_news(query):
    """Scrape Bing News search results for a query (no API key needed)."""
    articles = []
    encoded_query = quote_plus(query)
    url = f"https://www.bing.com/news/search?q={encoded_query}&form=NSBABR"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        # Bing News cards
        for card in soup.select("div.news-card, a.news-card"):
            title_el = card.select_one("a.title, div.title")
            snippet_el = card.select_one("div.snippet")
            source_el = card.select_one("div.source span, span.source")

            if not title_el:
                continue

            link = title_el.get("href", card.get("href", ""))
            if link and not link.startswith("http"):
                link = "https://www.bing.com" + link

            title = title_el.get_text(strip=True)
            summary = snippet_el.get_text(strip=True) if snippet_el else ""
            source = source_el.get_text(strip=True) if source_el else "Bing News"

            if not title or not link or not is_relevant(title, summary):
                continue

            articles.append({
                "title": title,
                "url": link,
                "source": source,
                "summary": summary[:1000],
                "published_date": None,
            })

        logger.info(f"  Bing News: found {len(articles)} relevant articles for '{query}'")

    except Exception as e:
        logger.warning(f"Bing News scrape failed for '{query}': {e}")

    return articles[:Config.MAX_ARTICLES_PER_RUN]


def save_articles(articles):
    """Save new articles to the database, skipping duplicates."""
    new_count = 0

    for article_data in articles:
        try:
            # Check if article already exists (by URL)
            existing = ScrapedArticle.select().where(
                ScrapedArticle.url == article_data["url"]
            ).first()

            if existing:
                continue

            # Extract full article content
            content = extract_article_content(article_data["url"])

            # Save to database
            ScrapedArticle.create(
                title=article_data["title"],
                url=article_data["url"],
                source=article_data["source"],
                summary=article_data["summary"],
                content=content,
                published_date=article_data.get("published_date"),
                is_relevant=True,
                blog_generated=False,
            )
            new_count += 1
            logger.info(f"📰 New article saved: {article_data['title']}")

            # Be polite - don't hammer servers
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error saving article: {e}")

    return new_count


def run_scraper():
    """Main scraper function - scrapes all configured sources (RSS, Google News, Bing News)."""
    logger.info("🔍 Starting news scrape...")
    total_found = 0
    total_new = 0
    errors = []

    # 1. RSS Feeds
    if Config.ENABLE_RSS_FEEDS:
        logger.info("📡 Scraping RSS feeds...")
        for feed_url in Config.RSS_FEEDS:
            try:
                logger.info(f"  Fetching: {feed_url[:80]}...")
                articles = parse_feed(feed_url)
                total_found += len(articles)

                if articles:
                    new = save_articles(articles)
                    total_new += new
                    logger.info(f"  Found {len(articles)} relevant, {new} new articles")

                time.sleep(2)

            except Exception as e:
                error_msg = f"RSS error ({feed_url[:50]}): {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

    # 2. Google News Web Scraping
    if Config.ENABLE_GOOGLE_NEWS:
        logger.info("🔎 Scraping Google News...")
        for query in Config.NEWS_SEARCH_QUERIES:
            try:
                articles = scrape_google_news(query)
                total_found += len(articles)

                if articles:
                    new = save_articles(articles)
                    total_new += new

                time.sleep(3)  # Be polite to Google

            except Exception as e:
                error_msg = f"Google News error ({query}): {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

    # 3. Bing News Web Scraping
    if Config.ENABLE_BING_NEWS:
        logger.info("🔎 Scraping Bing News...")
        for query in Config.NEWS_SEARCH_QUERIES:
            try:
                articles = scrape_bing_news(query)
                total_found += len(articles)

                if articles:
                    new = save_articles(articles)
                    total_new += new

                time.sleep(3)

            except Exception as e:
                error_msg = f"Bing News error ({query}): {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

    # Log the scrape run
    status = "success" if not errors else ("partial" if total_new > 0 else "failed")
    ScrapeLog.create(
        articles_found=total_found,
        articles_new=total_new,
        errors="\n".join(errors) if errors else "",
        status=status,
    )

    logger.info(f"✅ Scrape complete: {total_found} found, {total_new} new articles")
    return {"found": total_found, "new": total_new, "errors": errors}


def get_unprocessed_articles(limit=5):
    """Get articles that haven't been turned into blog posts yet."""
    return (
        ScrapedArticle.select()
        .where(
            (ScrapedArticle.blog_generated == False)
            & (ScrapedArticle.is_relevant == True)
        )
        .order_by(ScrapedArticle.scraped_at.desc())
        .limit(limit)
    )


# ===== DEMO DATA =====

def seed_demo_data():
    """Seed the database with demo articles for portfolio demonstration."""
    demo_articles = [
        {
            "title": "Major Sewage Spill Contaminates Lake Michigan Shoreline Near Chicago",
            "url": "https://example.com/demo/chicago-sewage-spill-2025",
            "source": "Environmental News Network",
            "summary": "A catastrophic sewage overflow event released approximately 1.2 billion gallons of untreated wastewater into Lake Michigan, prompting beach closures and drinking water advisories across the Chicago metropolitan area.",
            "content": """A catastrophic sewage overflow event released approximately 1.2 billion gallons of untreated wastewater into Lake Michigan near Chicago's South Side, prompting immediate beach closures and drinking water advisories across the metropolitan area.

The Metropolitan Water Reclamation District confirmed that the overflow was triggered by unprecedented rainfall that overwhelmed the city's aging combined sewer system. The incident began early Thursday morning when treatment capacity was exceeded at the Stickney Water Treatment Plant, the largest wastewater treatment facility in the world.

"This is one of the most significant overflow events we've seen in decades," said Dr. Maria Santos, environmental scientist at the University of Illinois at Chicago. "The volume of untreated sewage entering the lake poses serious risks to public health and aquatic ecosystems."

Water quality monitoring stations detected elevated levels of E. coli bacteria at more than 30 beach locations along the Illinois shoreline. The Illinois EPA has issued a do-not-swim advisory for all Lake Michigan beaches within a 50-mile radius of the discharge points.

The incident has renewed calls for infrastructure investment in wastewater treatment systems. The American Society of Civil Engineers estimates that the nation's wastewater infrastructure requires more than $271 billion in investments over the next 25 years.

Local environmental groups are demanding accountability and have announced plans to file a lawsuit under the Clean Water Act. "Combined sewer overflows are a persistent threat to public health and the environment," said Jennifer Walsh, director of the Lake Michigan Environmental Defense Coalition. "We need immediate action to separate storm and sanitary sewer systems."

The EPA has dispatched a team to assess the environmental damage and monitor water quality recovery. Officials estimate it could take several weeks for bacteria levels to return to safe limits.""",
            "published_date": datetime(2025, 11, 15, 10, 30),
        },
        {
            "title": "EPA Fines Texas Chemical Plant $4.5 Million for Illegal Wastewater Discharge",
            "url": "https://example.com/demo/texas-epa-fine-2025",
            "source": "Reuters Environmental",
            "summary": "The Environmental Protection Agency has levied a $4.5 million fine against Gulf Coast Chemicals Inc. for repeatedly discharging industrial wastewater containing toxic pollutants into Galveston Bay in violation of the Clean Water Act.",
            "content": """The Environmental Protection Agency announced a $4.5 million penalty against Gulf Coast Chemicals Inc., a Houston-area petrochemical manufacturer, for illegally discharging industrial wastewater containing toxic compounds into Galveston Bay over a three-year period.

According to the EPA's enforcement action, the company discharged wastewater containing benzene, toluene, and heavy metals at concentrations up to 50 times the permitted limits specified in their National Pollutant Discharge Elimination System (NPDES) permit.

"These violations represent a flagrant disregard for environmental law and public health," said EPA Region 6 Administrator Dr. Robert Chen. "Companies that knowingly pollute our waterways will face the full weight of federal enforcement."

The investigation, which began after complaints from local fishermen who noticed unusual discoloration in the bay waters, revealed that the company had been falsifying monitoring reports submitted to the Texas Commission on Environmental Quality.

Water quality testing conducted by EPA investigators found elevated levels of carcinogenic compounds in sediment samples taken near the company's discharge point. Several species of shellfish in the affected area showed signs of bioaccumulation of toxic metals.

The fine includes $3.2 million in civil penalties and $1.3 million in required environmental remediation projects. Gulf Coast Chemicals must also install advanced treatment systems capable of meeting discharge requirements within 18 months.

Environmental advocates welcomed the enforcement action but noted that penalties often fail to deter repeat offenders. "Fines need to be proportional to the damage caused," said environmental attorney Sarah Mitchell. "A $4.5 million fine for a company with annual revenues exceeding $2 billion is barely a slap on the wrist."

The case is part of a broader EPA initiative to crack down on industrial water pollution violators across the Gulf Coast region.""",
            "published_date": datetime(2025, 11, 14, 8, 0),
        },
        {
            "title": "New PFAS Treatment Technology Breakthrough at Municipal Wastewater Plants",
            "url": "https://example.com/demo/pfas-treatment-breakthrough",
            "source": "Water Technology Magazine",
            "summary": "Researchers at MIT have developed a novel electrochemical treatment process that can remove 99.9% of PFAS 'forever chemicals' from municipal wastewater at a fraction of the cost of existing methods.",
            "content": """A team of researchers at the Massachusetts Institute of Technology has announced a breakthrough in PFAS removal technology that could revolutionize how municipal wastewater treatment plants handle these persistent environmental contaminants.

The new electrochemical oxidation process, developed by Professor James Rodriguez and his team at MIT's Department of Chemical Engineering, uses specially designed electrode arrays to break down PFAS molecules into harmless byproducts. In laboratory and pilot-scale tests, the system achieved 99.9% removal of a broad spectrum of PFAS compounds.

"What makes our approach unique is that we're not just concentrating the PFAS — we're actually destroying them," said Professor Rodriguez. "The electrode materials we've developed create highly reactive conditions that cleave the carbon-fluorine bonds, which are among the strongest in organic chemistry."

PFAS (per- and polyfluoroalkyl substances), often called 'forever chemicals' because they do not break down naturally in the environment, have become one of the most pressing water quality challenges facing treatment utilities worldwide. The EPA recently established maximum contaminant levels for six PFAS compounds in drinking water.

The MIT system operates at a fraction of the cost of current PFAS treatment methods such as granular activated carbon and ion exchange resins. The researchers estimate that a full-scale system could treat wastewater at a cost of approximately $0.10 per 1,000 gallons, compared to $1.50 or more for conventional approaches.

Several municipal utilities have already expressed interest in pilot testing the technology. The Orange County Water District in California plans to install a demonstration unit at its Groundwater Replenishment System, the world's largest water purification facility for indirect potable reuse.

"If this technology performs as well at full scale as it does in the lab, it could be a game-changer for water utilities struggling to meet the new PFAS regulations," said Dr. Katherine Lee, chief technology officer at the American Water Works Association.

The research, funded by the National Science Foundation and the EPA, was published in the journal Nature Water. The team has filed for patent protection and is working with a startup company to commercialize the technology.""",
            "published_date": datetime(2025, 11, 13, 14, 0),
        },
        {
            "title": "UK Water Companies Face Criminal Charges Over Systematic Sewage Dumping",
            "url": "https://example.com/demo/uk-sewage-criminal-charges",
            "source": "The Guardian Environment",
            "summary": "Three major UK water companies are facing criminal prosecution after Ofwat investigations revealed systematic manipulation of sewage overflow monitoring equipment and deliberate illegal discharges into rivers.",
            "content": """Three of the UK's largest water and sewerage companies are facing criminal prosecution following extensive investigations by the water industry regulator Ofwat, which uncovered evidence of systematic sewage dumping and manipulation of environmental monitoring equipment.

Thames Water, Southern Water, and United Utilities have been referred to the Crown Prosecution Service after investigators found that the companies had deliberately tampered with storm overflow monitors and underreported the duration and volume of sewage discharges into rivers and coastal waters.

Environment Secretary David Miller described the findings as "a betrayal of public trust on an industrial scale." The investigation revealed that actual sewage discharge events were up to three times more frequent than reported, with some treatment works discharging continuously for weeks without triggering regulatory alerts.

"The evidence we have gathered shows a culture of systematic non-compliance that goes beyond individual incidents," said Ofwat Chief Executive Sarah Collins. "These companies have been hiding the true extent of sewage pollution from regulators, customers, and the public."

The charges come amid growing public outrage over the state of England's rivers and waterways. Campaign groups including Surfers Against Sewage and The Rivers Trust have documented widespread ecological damage linked to sewage pollution, including toxic algal blooms, fish kills, and the degradation of protected chalk streams.

Financial analysts warned that criminal convictions could have significant implications for the companies' ability to raise capital and service their substantial debt loads. Thames Water, which is already in financial distress, could face fines of up to 10% of annual turnover.

The companies have issued statements expressing regret and pledging to invest billions in infrastructure improvements. However, critics argue that decades of underinvestment and excessive dividend payments to shareholders have created a crisis that cannot be resolved quickly.

"These companies have prioritized profits over environmental protection for far too long," said Mark Lloyd, chief executive of The Rivers Trust. "Criminal prosecution sends a clear message that this behavior will no longer be tolerated."

A court date has been set for early 2026, in what is expected to be a landmark case for environmental enforcement in the UK.""",
            "published_date": datetime(2025, 11, 12, 16, 45),
        },
        {
            "title": "Florida Red Tide Worsened by Agricultural Runoff and Wastewater Discharges",
            "url": "https://example.com/demo/florida-red-tide-wastewater",
            "source": "Miami Herald",
            "summary": "Scientists have established a direct link between nutrient-rich wastewater discharges and the intensity of harmful algal blooms along Florida's Gulf Coast, calling for stricter treatment standards.",
            "content": """Marine scientists at the University of South Florida have published research establishing a definitive connection between nutrient-rich wastewater discharges and the severity of harmful algal blooms — commonly known as red tide — along Florida's Gulf Coast.

The peer-reviewed study, published in the Proceedings of the National Academy of Sciences, used satellite imagery, water sampling data, and advanced modeling techniques to track how nitrogen and phosphorus from wastewater treatment plant discharges and septic system failures fuel the explosive growth of Karenia brevis, the microscopic organism responsible for Florida's devastating red tide events.

"We've known for years that nutrients play a role in red tide, but this is the first study to quantify the contribution of wastewater to bloom intensity with this level of precision," said lead researcher Dr. Patricia Gomez. "Our analysis shows that areas with the highest density of wastewater discharge points correlate strongly with the most severe and prolonged bloom events."

The findings have significant implications for Florida's wastewater management policies. Many of the state's smaller municipalities still operate secondary treatment plants that remove only 85-90% of nutrients before discharge, compared to advanced treatment plants that achieve 99% nutrient removal.

Governor Lisa Chen has called for an emergency review of wastewater treatment standards statewide. "The connection between wastewater and red tide is now undeniable," the governor said in a press conference. "We must invest in upgrading our treatment infrastructure to protect our coastlines, tourism industry, and public health."

The economic impact of red tide events in Florida is substantial. A 2024 study estimated that severe bloom years cost the state's tourism and fishing industries more than $1 billion annually. The 2023 red tide event killed an estimated 2,000 tons of marine life along the Southwest Florida coast.

Environmental groups are calling for a statewide mandate to upgrade all wastewater treatment plants to advanced nutrient removal standards within ten years. The estimated cost of such an upgrade program is approximately $8 billion.

"Every dollar we invest in wastewater treatment upgrades will return multiple dollars in avoided environmental and economic damage," said Dr. Jessica Torres, policy director at the Florida Conservation Alliance.""",
            "published_date": datetime(2025, 11, 11, 9, 15),
        },
    ]

    count = 0
    for article in demo_articles:
        try:
            existing = ScrapedArticle.select().where(
                ScrapedArticle.url == article["url"]
            ).first()
            if not existing:
                ScrapedArticle.create(**article)
                count += 1
        except Exception as e:
            logger.error(f"Error seeding demo data: {e}")

    if count > 0:
        logger.info(f"🌱 Seeded {count} demo articles")

    return count


if __name__ == "__main__":
    from models import init_db
    init_db()

    logging.basicConfig(level=logging.INFO)
    result = run_scraper()
    print(f"\nScrape Results: {result}")
