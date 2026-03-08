#!/usr/bin/env python3
"""
Morning brief collection script
Runs automatically daily at 06:00, fetches global news RSS → data/morning_brief_YYYYMMDD.json
Coverage: Politics | Military | Economy | AI/LLM
"""
import json, pathlib, datetime, subprocess, re, sys, os, logging
from xml.etree import ElementTree as ET
from file_lock import atomic_json_write
from utils import validate_url

log = logging.getLogger('morning_brief')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

DATA = pathlib.Path(__file__).resolve().parent.parent / 'data'

# ── RSS feed configuration ──────────────────────────────────────────────────────────
FEEDS = {
    'Politics': [
        ('BBC World', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
        ('Reuters World', 'https://feeds.reuters.com/reuters/worldNews'),
        ('AP Top News', 'https://rsshub.app/apnews/topics/ap-top-news'),
    ],
    'Military': [
        ('Defense News', 'https://www.defensenews.com/rss/'),
        ('BBC World', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
        ('Reuters', 'https://feeds.reuters.com/reuters/worldNews'),
    ],
    'Economy': [
        ('Reuters Business', 'https://feeds.reuters.com/reuters/businessNews'),
        ('BBC Business', 'https://feeds.bbci.co.uk/news/business/rss.xml'),
        ('CNBC', 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114'),
    ],
    'AI/LLM': [
        ('Hacker News', 'https://hnrss.org/newest?q=AI+LLM+model&points=50'),
        ('VentureBeat AI', 'https://venturebeat.com/category/ai/feed/'),
        ('MIT Tech Review', 'https://www.technologyreview.com/feed/'),
    ],
}

CATEGORY_KEYWORDS = {
    'Military': ['war', 'military', 'troops', 'attack', 'missile', 'army', 'navy', 'weapons',
              'ukraine', 'russia', 'china sea', 'nato'],
    'AI/LLM': ['ai', 'llm', 'gpt', 'claude', 'gemini', 'openai', 'anthropic', 'deepseek',
                'machine learning', 'neural', 'model', 'chatgpt'],
}

def curl_rss(url, timeout=10):
    """Fetch RSS feed using curl"""
    try:
        r = subprocess.run(
            ['curl', '-s', '--max-time', str(timeout), '-L',
             '-A', 'Mozilla/5.0 (compatible; MorningBrief/1.0)',
             url],
            capture_output=True, timeout=timeout+2
        )
        return r.stdout.decode('utf-8', errors='ignore')
    except Exception:
        return ''

def _safe_parse_xml(xml_text, max_size=5*1024*1024):
    """Safely parse XML: limit size, disable external entities (prevent XXE)."""
    if len(xml_text) > max_size:
        log.warning(f'XML content too large ({len(xml_text)} bytes), skipping')
        return None
    # Strip DOCTYPE / ENTITY declarations to prevent XXE
    cleaned = re.sub(r'<!DOCTYPE[^>]*>', '', xml_text, flags=re.IGNORECASE)
    cleaned = re.sub(r'<!ENTITY[^>]*>', '', cleaned, flags=re.IGNORECASE)
    try:
        return ET.fromstring(cleaned)
    except ET.ParseError:
        return None


def parse_rss(xml_text):
    """Parse RSS XML → list of {title, desc, link, pub_date, image}"""
    items = []
    try:
        root = _safe_parse_xml(xml_text)
        if root is None:
            return items
        # RSS 2.0
        ns = {'media': 'http://search.yahoo.com/mrss/'}
        for item in root.findall('.//item')[:8]:
            def get(tag):
                el = item.find(tag)
                return (el.text or '').strip() if el is not None else ''
            title = get('title')
            desc  = re.sub(r'<[^>]+>', '', get('description'))[:200]
            link  = get('link')
            pub   = get('pubDate')
            # Image
            img = ''
            enc = item.find('enclosure')
            if enc is not None and 'image' in (enc.get('type') or ''):
                img = enc.get('url', '')
            media = item.find('media:thumbnail', ns) or item.find('media:content', ns)
            if media is not None:
                img = media.get('url', img)
            items.append({'title': title, 'desc': desc, 'link': link,
                          'pub_date': pub, 'image': img})
    except Exception:
        pass
    return items

def match_category(item, category):
    """Check if a news item belongs to a category (used for Military/AI filtering)"""
    kws = CATEGORY_KEYWORDS.get(category, [])
    if not kws:
        return True
    text = (item['title'] + ' ' + item['desc']).lower()
    return any(k in text for k in kws)

def fetch_category(category, feeds, max_items=5):
    """Fetch news for a category"""
    seen_urls = set()
    results = []
    for source_name, url in feeds:
        if len(results) >= max_items:
            break
        xml = curl_rss(url)
        if not xml:
            continue
        items = parse_rss(xml)
        for item in items:
            if not item['title']:
                continue
            if item['link'] in seen_urls:
                continue
            # Military and AI categories require keyword filtering
            if category in CATEGORY_KEYWORDS and not match_category(item, category):
                continue
            seen_urls.add(item['link'])
            results.append({
                'title': item['title'],
                'summary': item['desc'] or item['title'],
                'link': item['link'],
                'pub_date': item['pub_date'],
                'image': item['image'],
                'source': source_name,
            })
            if len(results) >= max_items:
                break
    return results

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='Force collection, ignore idempotency lock')
    args = parser.parse_args()

    # Idempotency lock: prevent duplicate execution
    today = datetime.date.today().strftime('%Y%m%d')
    lock_file = DATA / f'morning_brief_{today}.lock'
    if lock_file.exists() and not args.force:
        age = datetime.datetime.now().timestamp() - lock_file.stat().st_mtime
        if age < 3600:  # don't repeat within 1 hour
            log.info(f'Already collected today ({today}), skipping (use --force to override)')
            return
    # Note: write lock after successful collection to prevent locking on failure

    # Read user configuration
    config_file = DATA / 'morning_brief_config.json'
    config = {}
    try:
        config = json.loads(config_file.read_text())
    except Exception:
        pass

    # Enabled categories
    enabled_cats = set()
    if config.get('categories'):
        for c in config['categories']:
            if c.get('enabled', True):
                enabled_cats.add(c['name'])
    else:
        enabled_cats = set(FEEDS.keys())

    # User-defined keywords (globally weighted)
    user_keywords = [kw.lower() for kw in config.get('keywords', [])]

    # Merge custom RSS feeds
    custom_feeds = config.get('custom_feeds', [])
    merged_feeds = {}
    for cat, feeds in FEEDS.items():
        if cat in enabled_cats:
            merged_feeds[cat] = list(feeds)
    for cf in custom_feeds:
        cat = cf.get('category', '')
        feed_url = cf.get('url', '')
        if cat in enabled_cats and feed_url:
            # Validate custom feed URL (SSRF protection)
            if validate_url(feed_url):
                merged_feeds.setdefault(cat, []).append((cf.get('name', 'Custom'), feed_url))
            else:
                log.warning(f'Custom feed URL invalid, skipping: {feed_url}')

    log.info(f'Starting collection for {today}...')
    log.info(f'  Enabled categories: {", ".join(enabled_cats)}')
    if user_keywords:
        log.info(f'  Keywords: {", ".join(user_keywords)}')
    if custom_feeds:
        log.info(f'  Custom feeds: {len(custom_feeds)}')

    result = {
        'date': today,
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'categories': {}
    }

    for category, feeds in merged_feeds.items():
        log.info(f'  Collecting {category}...')
        items = fetch_category(category, feeds)
        # Boost items matching user keywords
        if user_keywords:
            for item in items:
                text = (item.get('title', '') + ' ' + item.get('summary', '')).lower()
                item['_kw_hits'] = sum(1 for kw in user_keywords if kw in text)
            items.sort(key=lambda x: x.get('_kw_hits', 0), reverse=True)
            for item in items:
                item.pop('_kw_hits', None)
        result['categories'][category] = items
        log.info(f'    {category}: {len(items)} items')

    # Write today's file
    today_file = DATA / f'morning_brief_{today}.json'
    atomic_json_write(today_file, result)

    # Overwrite latest (dashboard reads this)
    latest_file = DATA / 'morning_brief.json'
    atomic_json_write(latest_file, result)

    total = sum(len(v) for v in result['categories'].values())
    log.info(f'✅ Done: {total} news items → {today_file.name}')

    # Write idempotency lock only after successful collection
    lock_file.touch()

if __name__ == '__main__':
    main()
